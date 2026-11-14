package com.example.aurapostoassitance.ui.dashboard

import android.content.Context
import android.content.ContextWrapper
import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import androidx.compose.material.icons.rounded.Assessment
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Business
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DirectionsCar
import androidx.compose.material.icons.rounded.DocumentScanner
import androidx.compose.material.icons.rounded.Fingerprint
import androidx.compose.material.icons.rounded.LocalGasStation
import androidx.compose.material.icons.rounded.LocalShipping
import androidx.compose.material.icons.rounded.MedicalServices
import androidx.compose.material.icons.rounded.People
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.PointOfSale
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.ShoppingCart
import androidx.compose.material.icons.rounded.Stop
import androidx.compose.material.icons.rounded.Storefront
import androidx.compose.material.icons.automirrored.rounded.Chat
import androidx.compose.material.icons.automirrored.rounded.TrendingDown
import androidx.compose.material.icons.automirrored.rounded.VolumeUp
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.fragment.app.FragmentActivity
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.aurapostoassitance.ui.components.AuraAmbientBackground
import com.example.aurapostoassitance.ui.components.AuraLivingOrb
import com.example.aurapostoassitance.ui.components.AuraBottomGlassDock
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraChip
import com.example.aurapostoassitance.ui.components.AuraDynamicIsland
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.AuraNavTab
import com.example.aurapostoassitance.ui.components.LiquidGlassPill
import com.example.aurapostoassitance.ui.components.SectionLabel
import com.example.aurapostoassitance.ui.components.SpatialGlassCard
import com.example.aurapostoassitance.ui.vision.AuraVisionBottomSheet
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.components.findFragmentActivity
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.NewsreaderFamily
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianHigh
import com.example.aurapostoassitance.ui.theme.StatusSuccess
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary

private data class QuickTrigger(
    val title: String,
    val description: String,
    val icon: ImageVector,
    val accentColor: Color,
    val query: String
)

private val universalTriggers = listOf(
    QuickTrigger(
        title = "Previsão de Ruptura & Autonomia",
        description = "Previsão de esgotamento e economia estimada em compras preventivas antecipadas.",
        icon = Icons.Rounded.LocalGasStation,
        accentColor = AuraCyan,
        query = "Faça a previsão de esgotamento (Run-Out) e compras antecipadas dos estoques."
    ),
    QuickTrigger(
        title = "Detector de Fuga Invisível",
        description = "Auditoria de descontos sem alçada, divergências de caixa e vazamento de margem.",
        icon = Icons.AutoMirrored.Rounded.TrendingDown,
        accentColor = StatusWarning,
        query = "Audite as fugas invisíveis de lucro, desvios de caixa e descontos sem alçada."
    ),
    QuickTrigger(
        title = "Máquina Anti-Churn RFM",
        description = "Lote de clientes VIP e recorrentes em risco com templates Spintax de reativação.",
        icon = Icons.Rounded.People,
        accentColor = AuraPurple,
        query = "Gere o lote de clientes VIPs em risco de churn com mensagens de reativação no WhatsApp."
    ),
    QuickTrigger(
        title = "Conciliação Operacional & LMC",
        description = "Fechamento de turnos, conformidade legal ANP e conciliação de sangrias.",
        icon = Icons.Rounded.Assessment,
        accentColor = AuraEmerald,
        query = "Audite o fechamento de turno de hoje e conformidade operacional."
    ),
    QuickTrigger(
        title = "Olhos da AURA (Scanner Neural)",
        description = "Extração instantânea na NPU de Notas Fiscais (DANFE), tanques e fechamento.",
        icon = Icons.Rounded.DocumentScanner,
        accentColor = AuraPurple,
        query = "VISION_SCANNER_TRIGGER"
    ),
    QuickTrigger(
        title = "Retornos WhatsApp",
        description = "Acompanhe respostas do Contador, Gerente ou equipe em sessões dedicadas.",
        icon = Icons.AutoMirrored.Rounded.Chat,
        accentColor = AuraEmerald,
        query = "OPEN_WHATSAPP_RETURNS"
    )
)

private val chipPrompts = listOf(
    "Previsão de Ruptura 24h",
    "Fuga Invisível de Margem",
    "Clientes VIP em Risco",
    "Divergência de Caixa",
    "Auditoria LMC ANP",
    "Custo de Estoque Ocioso"
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    onNavigateToChat: (String?) -> Unit,
    onNavigateToSetup: () -> Unit = {},
    viewModel: DashboardViewModel = hiltViewModel()
) {
    var selectedTab by remember { mutableStateOf(AuraNavTab.PULSO) }
    val context = LocalContext.current
    val activity = remember(context) { context.findFragmentActivity() }
    var showVisionScanner by remember { mutableStateOf(false) }

    val selectedSegment by viewModel.selectedSegment.collectAsState()
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

    androidx.compose.runtime.LaunchedEffect(Unit) {
        selectedTab = AuraNavTab.PULSO
        viewModel.refreshHandoffSummary()
    }

    val isPlayingBriefing = isSpeaking && speakingMessageId == "briefing_$selectedSegment"

    AuraAmbientBackground {
        Scaffold(
            containerColor = Color.Transparent,
            topBar = {
                TopAppBar(
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            AuraBrandTitle(
                                text = "AURA",
                                style = MaterialTheme.typography.titleLarge
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            LiquidGlassPill(
                                text = "Super-Inteligência Online",
                                accentColor = StatusSuccess,
                                pulsingDot = true
                            )
                        }
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
                    onTabSelected = { tab ->
                        selectedTab = tab
                        when (tab) {
                            AuraNavTab.PULSO -> { /* Já no Pulso */ }
                            AuraNavTab.COCKPIT -> onNavigateToChat(null)
                            AuraNavTab.RETORNOS -> onNavigateToChat("OPEN_WHATSAPP_RETURNS")
                            AuraNavTab.TANQUES -> onNavigateToChat("Faça a previsão de esgotamento (Run-Out) dos recursos e mostre a situação de todos os compartimentos.")
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
                    .padding(horizontal = 20.dp, vertical = 12.dp)
            ) {
                // Banner de Modo Carro / Hands-Free Inteligente
                if (physicalContext.isCarModeActive) {
                    SpatialGlassCard(
                        modifier = Modifier.fillMaxWidth(),
                        accent = AuraEmerald,
                        iridescentBorder = true,
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
                                    modifier = Modifier.size(22.dp)
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
                    Spacer(modifier = Modifier.height(14.dp))
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
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Radar cognitivo da AURA com telemetria preditiva e modo sócio.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Telemetria de Silício & Hardware NPU (Qualcomm Snapdragon 7s Gen 2 / garnet)
                SpatialGlassCard(
                    modifier = Modifier.fillMaxWidth(),
                    accent = AuraPurple,
                    iridescentBorder = true,
                    contentPadding = PaddingValues(horizontal = 14.dp, vertical = 10.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.weight(1f)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(28.dp)
                                    .clip(CircleShape)
                                    .background(AuraPurple.copy(alpha = 0.22f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Rounded.AutoAwesome,
                                    contentDescription = null,
                                    tint = AuraPurple,
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = hardwareStatus.marketingName,
                                    style = MaterialTheme.typography.labelSmall.copy(
                                        fontWeight = FontWeight.Bold,
                                        letterSpacing = 0.5.sp
                                    ),
                                    color = TextPrimary,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Text(
                                    text = "${hardwareStatus.activeAccelerator} • ${hardwareStatus.cpuCores} Cores • Qualcomm TEE",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = TextMuted,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                        }
                        LiquidGlassPill(
                            text = "${"%.1f".format(hardwareStatus.lastInferenceLatencyMs)} ms",
                            accentColor = AuraEmerald,
                            pulsingDot = true
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Seletor de Segmentos Universais
                SectionLabel(text = "Segmento de Negócio Ativo")
                Spacer(modifier = Modifier.height(8.dp))
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(bottom = 4.dp)
                ) {
                    items(viewModel.availableSegments) { segment ->
                        val isSelected = segment.key == selectedSegment
                        val segIcon = when (segment.key) {
                            "postos_redes" -> Icons.Rounded.LocalGasStation
                            "varejo" -> Icons.Rounded.Storefront
                            "saas_b2b" -> Icons.Rounded.Business
                            "saude_clinicas" -> Icons.Rounded.MedicalServices
                            "ecommerce" -> Icons.Rounded.ShoppingCart
                            "logistica" -> Icons.Rounded.LocalShipping
                            else -> Icons.Rounded.AutoAwesome
                        }

                        AuraChip(
                            label = segment.label,
                            icon = segIcon,
                            onClick = { viewModel.selectSegment(segment.key) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // =============================================================
                // CARD BRIEFING MATINAL VOICE-FIRST (MODO SÓCIO)
                // =============================================================
                SpatialGlassCard(
                    modifier = Modifier.fillMaxWidth(),
                    accent = if (isPlayingBriefing) AuraPurple else AuraCyan,
                    glowActive = isPlayingBriefing,
                    iridescentBorder = true,
                    contentPadding = PaddingValues(18.dp)
                ) {
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .size(32.dp)
                                        .clip(CircleShape)
                                        .background(if (isPlayingBriefing) AuraPurple.copy(alpha = 0.25f) else AuraCyan.copy(alpha = 0.16f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = if (isPlayingBriefing) Icons.AutoMirrored.Rounded.VolumeUp else Icons.Rounded.AutoAwesome,
                                        contentDescription = null,
                                        tint = if (isPlayingBriefing) AuraPurple else AuraCyan,
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
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
                                        color = TextPrimary
                                    )
                                }
                            }

                            LiquidGlassPill(
                                text = if (isPlayingBriefing) "Voz Ativa" else "Pronto",
                                accentColor = if (isPlayingBriefing) AuraPurple else StatusSuccess,
                                pulsingDot = isPlayingBriefing
                            )
                        }

                        // Orbe Vivo e Fluido da AURA (Consciência visual orgânica líquida)
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            AuraLivingOrb(
                                sizeDp = 64.dp,
                                voiceRms = if (isPlayingBriefing) voiceAmplitude else 0.05f,
                                pulsing = true
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        when (val state = briefingState) {
                            is BriefingUiState.Loading -> {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 16.dp),
                                    horizontalArrangement = Arrangement.Center,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(24.dp),
                                        color = AuraCyan,
                                        strokeWidth = 2.dp
                                    )
                                    Spacer(modifier = Modifier.width(12.dp))
                                    Text(
                                        text = "Sintetizando diagnóstico executivo matinal...",
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
                                    style = MaterialTheme.typography.bodySmall.copy(
                                        lineHeight = 18.sp
                                    ),
                                    color = TextSecondary,
                                    maxLines = 4,
                                    overflow = TextOverflow.Ellipsis
                                )

                                Spacer(modifier = Modifier.height(16.dp))

                                // Botão de Áudio Voice-First
                                AuraGradientButton(
                                    text = if (isPlayingBriefing) "Pausar Áudio do Dia" else "Ouvir Resumo do Dia (45s)",
                                    icon = if (isPlayingBriefing) Icons.Rounded.Stop else Icons.Rounded.PlayArrow,
                                    onClick = { viewModel.togglePlayBriefing() },
                                    modifier = Modifier.fillMaxWidth()
                                )

                                Spacer(modifier = Modifier.height(16.dp))

                                // Ações de 1-Toque
                                Text(
                                    text = "GATILHOS DE 1 TOQUE (COMMAND JOURNAL)",
                                    style = MaterialTheme.typography.labelSmall.copy(
                                        letterSpacing = 0.8.sp,
                                        fontWeight = FontWeight.Bold
                                    ),
                                    color = TextMuted
                                )
                                Spacer(modifier = Modifier.height(8.dp))

                                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    briefing.suggestedActions.forEach { action ->
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clip(RoundedCornerShape(12.dp))
                                                .background(ObsidianBase.copy(alpha = 0.6f))
                                                .border(
                                                    width = 1.dp,
                                                    color = Color.White.copy(alpha = 0.08f),
                                                    shape = RoundedCornerShape(12.dp)
                                                )
                                                .clickable(enabled = !isExecutingAction && signedActions[action.code] == null) {
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
                                                        .background(AuraCyan.copy(alpha = 0.2f)),
                                                    contentAlignment = Alignment.Center
                                                ) {
                                                    Text(
                                                        text = action.code,
                                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
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
                                            val signedReceipt = signedActions[action.code]
                                            Row(
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                if (signedReceipt != null) {
                                                    Icon(
                                                        imageVector = Icons.Rounded.CheckCircle,
                                                        contentDescription = "Assinado TEE",
                                                        tint = AuraEmerald,
                                                        modifier = Modifier.size(15.dp)
                                                    )
                                                    Spacer(modifier = Modifier.width(4.dp))
                                                    Text(
                                                        text = "Assinado ($signedReceipt)",
                                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                                        color = AuraEmerald
                                                    )
                                                } else if (isExecutingAction) {
                                                    CircularProgressIndicator(
                                                        modifier = Modifier.size(14.dp),
                                                        strokeWidth = 2.dp,
                                                        color = AuraCyan
                                                    )
                                                    Spacer(modifier = Modifier.width(4.dp))
                                                    Text(
                                                        text = "Assinando...",
                                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                                        color = AuraCyan
                                                    )
                                                } else {
                                                    Icon(
                                                        imageVector = Icons.Rounded.Fingerprint,
                                                        contentDescription = "Assinatura TEE",
                                                        tint = AuraCyan,
                                                        modifier = Modifier.size(15.dp)
                                                    )
                                                    Spacer(modifier = Modifier.width(4.dp))
                                                    Text(
                                                        text = "Assinar TEE",
                                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                                        color = AuraCyan
                                                    )
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            BriefingUiState.Idle -> { /* Idle */ }
                        }
                    }
                }

                // Banner de Feedback do Command Journal
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
                            iridescentBorder = true,
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
                                        modifier = Modifier.size(20.dp)
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

                Spacer(modifier = Modifier.height(20.dp))

                // Dynamic Island de Telemetria Operacional
                AuraDynamicIsland(
                    onQueryAction = { query -> onNavigateToChat(query) }
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Pulse Status Bar (Glassmorphism Telemetria)
                SpatialGlassCard(
                    modifier = Modifier.fillMaxWidth(),
                    accent = AuraCyan,
                    iridescentBorder = true,
                    contentPadding = PaddingValues(16.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        PulseStatItem(label = "Recursos", value = "100% Ativos", dotColor = StatusSuccess)
                        PulseStatItem(label = "Fuga", value = "Monitorada", dotColor = AuraCyan)
                        PulseStatItem(label = "Anti-Churn", value = "Auditado", dotColor = AuraPurple)
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                SectionLabel(text = "Motores de Super-Inteligência Preditiva")
                Spacer(modifier = Modifier.height(12.dp))

                // 2x2 Triggers Grid Universais
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    universalTriggers.chunked(2).forEach { rowTriggers ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(IntrinsicSize.Max),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            rowTriggers.forEach { trigger ->
                                ExecutiveCard(
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

                Spacer(modifier = Modifier.height(26.dp))

                SectionLabel(text = "Consultas Frequentes")
                Spacer(modifier = Modifier.height(12.dp))

                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(bottom = 8.dp)
                ) {
                    items(chipPrompts) { prompt ->
                        AuraChip(
                            label = prompt,
                            icon = Icons.Rounded.AutoAwesome,
                            onClick = { onNavigateToChat(prompt) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(28.dp))

                // Main CTA AURA Button
                AuraGradientButton(
                    text = "Abrir AURA Chat",
                    onClick = { onNavigateToChat(null) },
                    icon = Icons.AutoMirrored.Rounded.Chat,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(24.dp))
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
    }
}

@Composable
private fun PulseStatItem(label: String, value: String, dotColor: Color) {
    Column {
        Text(
            text = label.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = TextMuted,
            letterSpacing = 0.5.sp
        )
        Spacer(modifier = Modifier.height(3.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusDot(color = dotColor, size = 6.dp, pulsing = true)
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = value,
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                color = TextPrimary
            )
        }
    }
}

@Composable
private fun ExecutiveCard(
    trigger: QuickTrigger,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    SpatialGlassCard(
        modifier = modifier.defaultMinSize(minHeight = 170.dp),
        accent = trigger.accentColor,
        iridescentBorder = true,
        onClick = onClick,
        contentPadding = PaddingValues(14.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .clip(CircleShape)
                    .background(trigger.accentColor.copy(alpha = 0.14f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = trigger.icon,
                    contentDescription = null,
                    tint = trigger.accentColor,
                    modifier = Modifier.size(20.dp)
                )
            }

            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = trigger.title,
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.SemiBold,
                        lineHeight = 19.sp
                    ),
                    color = TextPrimary
                )
                Text(
                    text = trigger.description,
                    style = MaterialTheme.typography.bodySmall.copy(
                        lineHeight = 15.sp
                    ),
                    color = TextSecondary,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}
