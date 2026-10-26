package com.example.aurapostoassitance.ui.setup

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Dns
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material.icons.rounded.VpnKey
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraGhostButton
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.SectionLabel
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuroraBrush
import com.example.aurapostoassitance.ui.theme.GlassHighlight
import com.example.aurapostoassitance.ui.theme.NewsreaderFamily
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianMid
import com.example.aurapostoassitance.ui.theme.OutlineSoft
import com.example.aurapostoassitance.ui.theme.StatusDanger
import com.example.aurapostoassitance.ui.theme.StatusSuccess
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary

@Composable
fun SetupScreen(
    onSetupComplete: () -> Unit,
    viewModel: SetupViewModel = hiltViewModel()
) {
    var ipAddress by remember { mutableStateOf(viewModel.getInitialIp()) }
    var isLoading by remember { mutableStateOf(false) }
    val isScanning by viewModel.isScanning.collectAsState()
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var scanStatusMessage by remember { mutableStateOf<String?>(null) }
    val keyboardController = LocalSoftwareKeyboardController.current

    val tailscaleDefaultIp = "100.77.164.17:8000"

    fun performConnection(targetIp: String) {
        isLoading = true
        errorMessage = null
        scanStatusMessage = null
        keyboardController?.hide()
        viewModel.testConnection(targetIp) { success ->
            isLoading = false
            if (success) {
                onSetupComplete()
            } else {
                errorMessage = "Falha ao conectar em $targetIp. Verifique se o servidor AURA está ativo na rede."
            }
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(ObsidianBase)
            .padding(horizontal = 24.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Spacer(modifier = Modifier.height(36.dp))

            // Logo & Title Deluxe
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(CircleShape)
                    .background(AuroraBrush)
                    .border(2.dp, Color(0x44FFFFFF), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "A",
                    style = MaterialTheme.typography.displayMedium.copy(
                        fontFamily = NewsreaderFamily,
                        fontWeight = FontWeight.Bold,
                        fontSize = 36.sp
                    ),
                    color = ObsidianBase
                )
            }

            Spacer(modifier = Modifier.height(18.dp))

            AuraBrandTitle(
                text = "AURA",
                style = MaterialTheme.typography.displayMedium.copy(
                    fontFamily = NewsreaderFamily
                ),
                letterSpacing = 2.sp
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Conexão com a Inteligência Local do Posto",
                style = MaterialTheme.typography.bodyMedium,
                color = TextSecondary
            )

            Spacer(modifier = Modifier.height(34.dp))

            // Tailscale 1-Tap Quick Connect Card
            AuraCard(
                modifier = Modifier.fillMaxWidth(),
                accent = AuraCyan,
                contentPadding = PaddingValues(16.dp),
                onClick = {
                    ipAddress = tailscaleDefaultIp
                    performConnection(tailscaleDefaultIp)
                }
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .clip(CircleShape)
                            .background(AuraCyan.copy(alpha = 0.14f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.VpnKey,
                            contentDescription = null,
                            tint = AuraCyan,
                            modifier = Modifier.size(22.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "Conectar via Tailscale",
                                style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.SemiBold),
                                color = TextPrimary
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            StatusDot(color = StatusSuccess, size = 6.dp, pulsing = true)
                        }
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = tailscaleDefaultIp,
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(22.dp))

            SectionLabel(text = "Ou buscar na rede local")
            Spacer(modifier = Modifier.height(12.dp))

            // Scan Button
            AuraGhostButton(
                text = if (isScanning) "Buscando Servidor no Wi-Fi..." else "Autodetectar na Rede Local",
                icon = Icons.Rounded.Search,
                onClick = {
                    errorMessage = null
                    scanStatusMessage = "Escaneando portas na rede Wi-Fi..."
                    viewModel.scanNetworkForServer(
                        onFound = { foundIp ->
                            ipAddress = foundIp
                            scanStatusMessage = "Servidor detectado em $foundIp!"
                            performConnection(foundIp)
                        },
                        onNotFound = {
                            scanStatusMessage = null
                            errorMessage = "Nenhum servidor AURA encontrado no Wi-Fi. Digite o IP manualmente."
                        }
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                tint = AuraEmerald
            )

            if (scanStatusMessage != null) {
                Spacer(modifier = Modifier.height(10.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    StatusDot(color = StatusSuccess, size = 6.dp, pulsing = true)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = scanStatusMessage!!,
                        color = StatusSuccess,
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            SectionLabel(text = "Endereço Manual")
            Spacer(modifier = Modifier.height(12.dp))

            val inputInteraction = remember { MutableInteractionSource() }
            val inputFocused by inputInteraction.collectIsFocusedAsState()
            val inputBorderColor by animateColorAsState(
                targetValue = if (inputFocused) AuraCyan else OutlineSoft,
                animationSpec = tween(250),
                label = "inputBorder"
            )
            val inputShape = RoundedCornerShape(16.dp)

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(inputShape)
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
                    .border(1.dp, inputBorderColor, inputShape)
                    .padding(horizontal = 16.dp, vertical = 14.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Dns,
                        contentDescription = null,
                        tint = if (inputFocused) AuraCyan else TextMuted,
                        modifier = Modifier.size(20.dp)
                    )
                    Box(modifier = Modifier.weight(1f)) {
                        if (ipAddress.isEmpty()) {
                            Text(
                                text = "IP e Porta (ex: 100.77.164.17:8000)",
                                style = MaterialTheme.typography.bodyLarge,
                                color = TextMuted
                            )
                        }
                        BasicTextField(
                            value = ipAddress,
                            onValueChange = {
                                ipAddress = it
                                errorMessage = null
                            },
                            interactionSource = inputInteraction,
                            textStyle = MaterialTheme.typography.bodyLarge.copy(color = TextPrimary),
                            cursorBrush = SolidColor(AuraCyan),
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Uri,
                                imeAction = ImeAction.Done
                            ),
                            keyboardActions = KeyboardActions(
                                onDone = {
                                    if (ipAddress.isNotBlank() && !isLoading) {
                                        performConnection(ipAddress)
                                    }
                                }
                            ),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }

            if (errorMessage != null) {
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    StatusDot(color = StatusDanger, size = 6.dp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = errorMessage!!,
                        color = StatusDanger,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            Spacer(modifier = Modifier.height(30.dp))

            if (isLoading) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
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
                        text = "Verificando saúde do servidor AURA...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary
                    )
                }
            } else {
                AuraGradientButton(
                    text = "Conectar ao Posto",
                    onClick = { performConnection(ipAddress) },
                    enabled = ipAddress.isNotBlank() && !isScanning,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            Spacer(modifier = Modifier.height(36.dp))
        }
    }
}
