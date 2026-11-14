package com.example.aurapostoassitance.ui.vision

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.content.FileProvider
import java.io.File
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.CameraAlt
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DocumentScanner
import androidx.compose.material.icons.rounded.PhotoLibrary
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
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
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import com.example.aurapostoassitance.data.vision.AuraVisionNpuScanner
import com.example.aurapostoassitance.data.vision.ScannedDocumentTelemetry
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.LiquidGlassPill
import com.example.aurapostoassitance.ui.components.SpatialGlassCard
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.StatusSuccess
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary
import kotlinx.coroutines.launch

/**
 * Interface espacial dos "Olhos da AURA" — Scanner Neural On-Device via NPU.
 * Permite capturar ou selecionar documentos operacionais (DANFEs, medição de tanques, fechamentos)
 * com extração em milissegundos e envio direto para auditoria.
 */
@Composable
fun AuraVisionBottomSheet(
    onDismiss: () -> Unit,
    onAuditWithAura: (ScannedDocumentTelemetry) -> Unit,
    scanner: AuraVisionNpuScanner,
    onDocumentCaptured: (uri: Uri, title: String) -> Unit = { _, _ -> }
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var isScanning by remember { mutableStateOf(false) }
    var scannedResult by remember { mutableStateOf<ScannedDocumentTelemetry?>(null) }
    var lastScannedUri by remember { mutableStateOf<Uri?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var pendingCameraUri by remember { mutableStateOf<Uri?>(null) }

    fun processScannedUri(uri: Uri) {
        isScanning = true
        errorMessage = null
        scope.launch {
            try {
                val result = scanner.scanUri(uri)
                if (result.rawText.isBlank()) {
                    scannedResult = null
                    errorMessage = "Não consegui extrair texto ou código legível. Aproxime mais da nota ou envie PDF/XML original."
                } else {
                    scannedResult = result
                    lastScannedUri = uri
                    val previewUri = result.previewImagePath?.let { Uri.fromFile(File(it)) } ?: uri
                    onDocumentCaptured(previewUri, result.title)
                }
            } catch (e: Exception) {
                errorMessage = "Erro ao processar imagem na NPU: ${e.localizedMessage}"
            } finally {
                isScanning = false
            }
        }
    }

    val takePictureLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success: Boolean ->
        val uri = pendingCameraUri
        if (success && uri != null) {
            processScannedUri(uri)
        } else if (success) {
            errorMessage = "Não foi possível recuperar a foto capturada."
        }
    }

    fun startHighResCamera() {
        runCatching {
            val cacheDir = File(context.cacheDir, "vision_scans").apply { mkdirs() }
            val photoFile = File(cacheDir, "scan_${System.currentTimeMillis()}.jpg")
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                photoFile
            )
            pendingCameraUri = uri
            takePictureLauncher.launch(uri)
        }.onFailure {
            errorMessage = "Não foi possível abrir a câmera: ${it.localizedMessage}"
        }
    }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startHighResCamera()
        } else {
            errorMessage = "Permissão de câmera necessária para escanear documentos."
        }
    }

    val launchCamera = {
        errorMessage = null
        val hasPermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
        if (hasPermission) {
            startHighResCamera()
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    val pickDocumentLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        if (uri != null) {
            processScannedUri(uri)
        }
    }

    val launchGallery = {
        errorMessage = null
        runCatching {
            pickDocumentLauncher.launch(arrayOf("image/*", "application/pdf", "text/xml", "application/xml"))
        }.onFailure { errorMessage = "Não foi possível abrir os arquivos: ${it.localizedMessage}" }
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            decorFitsSystemWindows = false
        )
    ) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.72f))
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
                    .navigationBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 24.dp)
                    .clickable(
                        interactionSource = remember { MutableInteractionSource() },
                        indication = null
                    ) { /* Consome cliques dentro do card */ },
                accent = AuraCyan,
                iridescentBorder = true,
                contentPadding = PaddingValues(20.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState())
                ) {
                    // Header com Identificação Neural
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(AuraCyan.copy(alpha = 0.2f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Rounded.DocumentScanner,
                                    contentDescription = null,
                                    tint = AuraCyan,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                AuraBrandTitle(
                                    text = "OLHOS DA AURA",
                                    style = MaterialTheme.typography.titleMedium
                                )
                                Text(
                                    text = "Scanner Neural On-Device • Qualcomm Hexagon NPU",
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
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    if (isScanning) {
                        // Estado de Processamento na NPU
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 24.dp),
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(28.dp),
                                color = AuraCyan,
                                strokeWidth = 2.5.dp
                            )
                            Spacer(modifier = Modifier.width(14.dp))
                            Column {
                                Text(
                                    text = "Processando visão na Hexagon NPU...",
                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                                    color = TextPrimary
                                )
                                Text(
                                    text = "Extração neural de CNPJs, volumes e valores",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = TextMuted
                                )
                            }
                        }
                    } else if (scannedResult != null) {
                        // Resultado Escaneado
                        val result = scannedResult!!
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = result.title,
                                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                                color = TextPrimary
                            )
                            LiquidGlassPill(
                                text = "${result.scanLatencyMs} ms (NPU)",
                                accentColor = AuraEmerald,
                                pulsingDot = true
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                                .background(ObsidianBase.copy(alpha = 0.8f))
                                .padding(14.dp)
                        ) {
                            Column {
                                Text(
                                    text = result.executiveSummary,
                                    style = MaterialTheme.typography.bodySmall.copy(lineHeight = 20.sp),
                                    color = TextSecondary
                                )
                                if (result.rawText.isNotBlank()) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(
                                        text = "Prévia lida: ${result.rawText.replace("\n", " ").take(180)}...",
                                        style = MaterialTheme.typography.labelSmall.copy(lineHeight = 16.sp),
                                        color = TextMuted,
                                        maxLines = 3,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        // Botões de Ação com o Resultado
                        AuraGradientButton(
                            text = "Auditar com a AURA",
                            icon = Icons.Rounded.AutoAwesome,
                            onClick = {
                                val attachUri = result.previewImagePath?.let { Uri.fromFile(File(it)) } ?: lastScannedUri
                                attachUri?.let { uri -> onDocumentCaptured(uri, result.title) }
                                onAuditWithAura(result)
                                onDismiss()
                            },
                            modifier = Modifier.fillMaxWidth()
                        )

                        Spacer(modifier = Modifier.height(10.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            AuraGradientButton(
                                text = "Tirar Outra Foto",
                                icon = Icons.Rounded.CameraAlt,
                                onClick = { launchCamera() },
                                modifier = Modifier.weight(1f)
                            )
                            AuraGradientButton(
                                text = "Galeria",
                                icon = Icons.Rounded.PhotoLibrary,
                                onClick = { launchGallery() },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    } else {
                        // Estado Inicial de Escolha de Captura
                        Text(
                            text = "Aponte a câmera para uma Nota Fiscal (DANFE), visor Veeder-Root de tanques, relatório de turno ou placa de preços para extração neural instantânea no silício.",
                            style = MaterialTheme.typography.bodySmall.copy(lineHeight = 18.sp),
                            color = TextSecondary
                        )

                        if (errorMessage != null) {
                            Spacer(modifier = Modifier.height(10.dp))
                            Text(
                                text = errorMessage!!,
                                style = MaterialTheme.typography.labelSmall,
                                color = StatusWarning
                            )
                        }

                        Spacer(modifier = Modifier.height(18.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            AuraGradientButton(
                                text = "Câmera (DANFE/Tanque)",
                                icon = Icons.Rounded.CameraAlt,
                                onClick = { launchCamera() },
                                modifier = Modifier.weight(1f)
                            )
                            AuraGradientButton(
                                text = "Foto / PDF / XML",
                                icon = Icons.Rounded.PhotoLibrary,
                                onClick = { launchGallery() },
                                modifier = Modifier.weight(1f)
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))
                        Text(
                            text = "🔒 100% On-Device: A imagem é processada localmente na NPU sem trafegar fotos pela internet.",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted,
                            fontSize = 11.sp
                        )
                    }
                }
            }
        }
    }
    }
}
