package com.example.aurapostoassitance.ui.assist

import android.content.Intent
import android.os.Bundle
import androidx.fragment.app.FragmentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Chat
import androidx.compose.material.icons.automirrored.rounded.TrendingDown
import androidx.compose.material.icons.automirrored.rounded.VolumeUp
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DocumentScanner
import androidx.compose.material.icons.rounded.LocalGasStation
import androidx.compose.material.icons.rounded.Mic
import androidx.compose.material.icons.rounded.People
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Stop
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.MainActivity
import com.example.aurapostoassitance.data.audio.AuraDirectVoiceAction
import com.example.aurapostoassitance.data.audio.AuraVoiceCommandRouter
import com.example.aurapostoassitance.data.audio.AuraVoiceManager
import com.example.aurapostoassitance.data.local.AuraOfflineVault
import com.example.aurapostoassitance.data.npu.AuraNpuEngine
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraLivingOrb
import com.example.aurapostoassitance.ui.components.AuraChip
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.LiquidGlassPill
import com.example.aurapostoassitance.ui.components.SpatialGlassCard
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPostoAssitanceTheme
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.StatusSuccess
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class AuraAssistActivity : FragmentActivity() {

    @Inject
    lateinit var voiceManager: AuraVoiceManager

    @Inject
    lateinit var offlineVault: AuraOfflineVault

    @Inject
    lateinit var npuEngine: AuraNpuEngine

    @Inject
    lateinit var voiceCommandRouter: AuraVoiceCommandRouter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            AuraPostoAssitanceTheme {
                AssistOverlayContent(
                    onDismiss = { finish() },
                    onNavigateToChat = { query ->
                        val intent = Intent(this, MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                            if (query != null) {
                                putExtra("aura_query", query)
                            }
                        }
                        startActivity(intent)
                        finish()
                    },
                    voiceManager = voiceManager,
                    offlineVault = offlineVault,
                    npuEngine = npuEngine,
                    voiceCommandRouter = voiceCommandRouter
                )
            }
        }
    }
}

@Composable
private fun AssistOverlayContent(
    onDismiss: () -> Unit,
    onNavigateToChat: (String?) -> Unit,
    voiceManager: AuraVoiceManager,
    offlineVault: AuraOfflineVault,
    npuEngine: AuraNpuEngine,
    voiceCommandRouter: AuraVoiceCommandRouter
) {
    val isSpeaking by voiceManager.isSpeaking.collectAsState()
    val isListening by voiceManager.isListening.collectAsState()
    val voiceAmplitude by voiceManager.voiceAmplitude.collectAsState()
    val hardwareStatus by npuEngine.hardwareStatus.collectAsState()

    val briefing = remember { offlineVault.getBriefing("postos_redes") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null
            ) { onDismiss() },
        contentAlignment = Alignment.BottomCenter
    ) {
        AnimatedVisibility(
            visible = true,
            enter = fadeIn() + slideInVertically(initialOffsetY = { it / 2 })
        ) {
            SpatialGlassCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 24.dp)
                    .clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = null
                    ) { /* Consome toque dentro do card */ },
                accent = AuraCyan,
                glowActive = isListening || isSpeaking,
                iridescentBorder = true,
                contentPadding = PaddingValues(20.dp)
            ) {
                Column(modifier = Modifier.fillMaxWidth()) {
                    // Header com tag de silício NPU
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            AuraLivingOrb(
                                sizeDp = 40.dp,
                                voiceRms = voiceAmplitude,
                                pulsing = true
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                AuraBrandTitle(
                                    text = "AURA ASSISTANT",
                                    style = MaterialTheme.typography.titleMedium
                                )
                                Text(
                                    text = "${hardwareStatus.marketingName} • Hexagon NPU + TEE",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = TextMuted,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                        }

                        IconButton(
                            onClick = onDismiss,
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Rounded.Close,
                                contentDescription = "Fechar",
                                tint = TextMuted,
                                modifier = Modifier.size(18.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Status e Resumo Rápido
                    Text(
                        text = briefing.oralVoiceScript,
                        style = MaterialTheme.typography.bodySmall.copy(
                            lineHeight = 17.sp
                        ),
                        color = TextSecondary,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    // Botão Voice-First Ouvir / Pausar
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        AuraGradientButton(
                            text = if (isSpeaking) "Pausar Briefing" else "Ouvir Resumo (45s)",
                            icon = if (isSpeaking) Icons.Rounded.Stop else Icons.Rounded.PlayArrow,
                            onClick = {
                                if (isSpeaking) {
                                    voiceManager.stopSpeaking()
                                } else {
                                    voiceManager.speak("assist_briefing", briefing.oralVoiceScript)
                                }
                            },
                            modifier = Modifier.weight(1f)
                        )

                        AuraGradientButton(
                            text = if (isListening) "Ouvindo..." else "Falar",
                            icon = if (isListening) Icons.AutoMirrored.Rounded.VolumeUp else Icons.Rounded.Mic,
                            onClick = {
                                if (isListening) {
                                    voiceManager.stopListening()
                                } else {
                                    voiceManager.startListening { query ->
                                        if (query.isNotBlank()) {
                                            val commandResult = voiceCommandRouter.routeSpokenText(query)
                                            when (commandResult.action) {
                                                AuraDirectVoiceAction.STOP_AUDIO -> {
                                                    voiceManager.stopSpeaking()
                                                }
                                                AuraDirectVoiceAction.PLAY_BRIEFING -> {
                                                    voiceManager.speak("assist_briefing", briefing.oralVoiceScript)
                                                }
                                                AuraDirectVoiceAction.EXECUTE_OPTION_1 -> {
                                                    onNavigateToChat("Aprovar reposição de combustível prioridade 1.")
                                                }
                                                AuraDirectVoiceAction.OPEN_VISION_SCANNER -> {
                                                    onNavigateToChat("Abra os Olhos da AURA para escanear uma nota fiscal ou documento operacional.")
                                                }
                                                AuraDirectVoiceAction.FALLBACK_CHAT_QUERY -> {
                                                    onNavigateToChat(query)
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            modifier = Modifier.weight(0.8f)
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Chips de Ação Rápida
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        AuraChip(
                            label = "Ruptura 24h",
                            icon = Icons.Rounded.LocalGasStation,
                            onClick = {
                                onNavigateToChat("Faça a previsão de esgotamento (Run-Out) e compras antecipadas.")
                            }
                        )
                        AuraChip(
                            label = "Fuga de Caixa",
                            icon = Icons.AutoMirrored.Rounded.TrendingDown,
                            onClick = {
                                onNavigateToChat("Audite as fugas invisíveis de lucro e descontos sem alçada.")
                            }
                        )
                        AuraChip(
                            label = "Anti-Churn",
                            icon = Icons.Rounded.People,
                            onClick = {
                                onNavigateToChat("Gere o lote de clientes VIPs em risco de churn.")
                            }
                        )
                        AuraChip(
                            label = "Escanear Nota",
                            icon = Icons.Rounded.DocumentScanner,
                            onClick = {
                                onNavigateToChat("Abra os Olhos da AURA para escanear uma nota fiscal ou documento operacional.")
                            }
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // Rodapé com link para Cockpit completo
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .clickable { onNavigateToChat(null) }
                            .padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Rounded.Chat,
                            contentDescription = null,
                            tint = AuraCyan,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Abrir Cockpit Completo da AURA",
                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                            color = AuraCyan
                        )
                    }
                }
            }
        }
    }
}
