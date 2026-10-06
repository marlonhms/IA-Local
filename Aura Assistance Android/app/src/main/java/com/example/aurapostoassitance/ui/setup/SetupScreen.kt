package com.example.aurapostoassitance.ui.setup

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald

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

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "AURA",
            style = MaterialTheme.typography.displayLarge,
            color = AuraEmerald,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Assistente de Prontidão Executiva",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(bottom = 32.dp)
        )

        OutlinedButton(
            onClick = {
                errorMessage = null
                scanStatusMessage = "🔍 Escaneando a rede Wi-Fi local..."
                viewModel.scanNetworkForServer(
                    onFound = { foundIp ->
                        ipAddress = foundIp
                        scanStatusMessage = "⛽ Servidor localizado em $foundIp!"
                        // Automatically test connection and enter
                        isLoading = true
                        viewModel.testConnection(foundIp) { success ->
                            isLoading = false
                            if (success) {
                                onSetupComplete()
                            } else {
                                errorMessage = "Servidor encontrado em $foundIp, mas não respondeu ao health check."
                            }
                        }
                    },
                    onNotFound = {
                        scanStatusMessage = null
                        errorMessage = "Nenhum servidor AURA encontrado no Wi-Fi. Verifique a conexão ou digite o IP manualmente."
                    }
                )
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp),
            enabled = !isLoading && !isScanning,
            colors = ButtonDefaults.outlinedButtonColors(
                contentColor = AuraCyan
            )
        ) {
            if (isScanning) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = AuraCyan,
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Procurando Servidor no Wi-Fi...", fontWeight = FontWeight.Bold)
                }
            } else {
                Text("🔍 Autodetectar Servidor na Rede", fontWeight = FontWeight.Bold)
            }
        }

        if (scanStatusMessage != null) {
            Text(
                text = scanStatusMessage!!,
                color = AuraEmerald,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(top = 8.dp)
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        OutlinedTextField(
            value = ipAddress,
            onValueChange = { ipAddress = it },
            label = { Text("IP do Servidor Local / Tailscale") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            isError = errorMessage != null
        )

        if (errorMessage != null) {
            Text(
                text = errorMessage!!,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 4.dp, bottom = 16.dp)
            )
        } else {
            Spacer(modifier = Modifier.height(16.dp))
        }

        Button(
            onClick = {
                isLoading = true
                errorMessage = null
                viewModel.testConnection(ipAddress) { success ->
                    isLoading = false
                    if (success) {
                        onSetupComplete()
                    } else {
                        errorMessage = "Falha ao conectar. Verifique o IP e se o servidor FastAPI está rodando na rede local."
                    }
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp),
            enabled = !isLoading && !isScanning && ipAddress.isNotBlank()
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    color = MaterialTheme.colorScheme.onPrimary
                )
            } else {
                Text("Conectar Manualmente", fontWeight = FontWeight.Bold)
            }
        }
    }
}
