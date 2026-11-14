package com.example.aurapostoassitance.ui.vision

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.Crop
import androidx.compose.material.icons.rounded.CropFree
import androidx.compose.material.icons.rounded.RotateRight
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.AuraGhostButton
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.GlassBorderSoft
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.roundToInt

private enum class DragTarget {
    NONE,
    TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT,
    LEFT_EDGE, RIGHT_EDGE, TOP_EDGE, BOTTOM_EDGE,
    MOVE_BOX
}

/**
 * Editor interativo on-device para recortar e girar a foto antes da leitura na NPU.
 * Mantém a resolução nativa (até 2200px) para preservar códigos de barras e textos pequenos.
 */
@Composable
fun AuraImageCropEditor(
    sourceUri: Uri,
    onCancel: () -> Unit,
    onCroppedReady: (croppedUri: Uri) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val density = LocalDensity.current

    var rotationSteps by remember(sourceUri) { mutableIntStateOf(0) }
    var baseBitmap by remember(sourceUri) { mutableStateOf<Bitmap?>(null) }
    var displayBitmap by remember(sourceUri) { mutableStateOf<Bitmap?>(null) }
    var loadError by remember(sourceUri) { mutableStateOf<String?>(null) }
    var isSavingCrop by remember { mutableStateOf(false) }

    // Coordenadas normalizadas do retângulo de corte (0f..1f sobre a imagem exibida)
    var leftF by remember(sourceUri) { mutableFloatStateOf(0.05f) }
    var topF by remember(sourceUri) { mutableFloatStateOf(0.05f) }
    var rightF by remember(sourceUri) { mutableFloatStateOf(0.95f) }
    var bottomF by remember(sourceUri) { mutableFloatStateOf(0.95f) }

    LaunchedEffect(sourceUri) {
        loadError = null
        val loaded = withContext(Dispatchers.IO) {
            loadUprightBitmap(context, sourceUri, maxEdge = 2200)
        }
        if (loaded == null) {
            loadError = "Não foi possível carregar a imagem para recorte."
        } else {
            baseBitmap = loaded
            displayBitmap = loaded
        }
    }

    fun applyRotation() {
        val current = baseBitmap ?: return
        rotationSteps = (rotationSteps + 1) % 4
        val rotated = rotateBitmap(current, rotationSteps * 90f)
        displayBitmap = rotated
        leftF = 0.05f
        topF = 0.05f
        rightF = 0.95f
        bottomF = 0.95f
    }

    fun exportAndScan(fullImage: Boolean) {
        val bmp = displayBitmap ?: return
        isSavingCrop = true
        scope.launch {
            val outUri = withContext(Dispatchers.IO) {
                runCatching {
                    val cropX = if (fullImage) 0 else (leftF * bmp.width).roundToInt().coerceIn(0, bmp.width - 1)
                    val cropY = if (fullImage) 0 else (topF * bmp.height).roundToInt().coerceIn(0, bmp.height - 1)
                    val cropW = if (fullImage) bmp.width else ((rightF - leftF) * bmp.width).roundToInt().coerceIn(20, bmp.width - cropX)
                    val cropH = if (fullImage) bmp.height else ((bottomF - topF) * bmp.height).roundToInt().coerceIn(20, bmp.height - cropY)

                    val finalBmp = if (cropX == 0 && cropY == 0 && cropW == bmp.width && cropH == bmp.height) {
                        bmp
                    } else {
                        Bitmap.createBitmap(bmp, cropX, cropY, cropW, cropH)
                    }

                    val dir = File(context.cacheDir, "vision_scans").apply { mkdirs() }
                    val outFile = File(dir, "cropped_${System.currentTimeMillis()}.jpg")
                    FileOutputStream(outFile).use { fos ->
                        finalBmp.compress(Bitmap.CompressFormat.JPEG, 92, fos)
                    }
                    if (finalBmp !== bmp) finalBmp.recycle()

                    FileProvider.getUriForFile(
                        context,
                        "${context.packageName}.fileprovider",
                        outFile
                    )
                }.getOrNull()
            }
            isSavingCrop = false
            if (outUri != null) {
                onCroppedReady(outUri)
            } else {
                loadError = "Falha ao salvar recorte da imagem."
            }
        }
    }

    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = "Recortar e Focar Área",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    color = TextPrimary
                )
                Text(
                    text = "Arraste os cantos para isolar itens, totais ou código de barras",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextMuted
                )
            }
            TextButton(onClick = { applyRotation() }, enabled = displayBitmap != null && !isSavingCrop) {
                Icon(Icons.Rounded.RotateRight, contentDescription = "Girar 90 graus", tint = AuraCyan, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(4.dp))
                Text("Girar", color = AuraCyan, style = MaterialTheme.typography.labelMedium)
            }
        }

        Spacer(Modifier.height(8.dp))

        BoxWithConstraints(
            modifier = Modifier
                .fillMaxWidth()
                .height(340.dp)
                .clip(RoundedCornerShape(14.dp))
                .background(ObsidianBase)
                .border(1.dp, GlassBorderSoft, RoundedCornerShape(14.dp)),
            contentAlignment = Alignment.Center
        ) {
            val bmp = displayBitmap
            if (loadError != null) {
                Text(text = loadError!!, color = Color(0xFFFFB74D), style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(16.dp))
            } else if (bmp == null) {
                CircularProgressIndicator(color = AuraCyan, modifier = Modifier.size(30.dp))
            } else {
                val containerW = with(density) { maxWidth.toPx() }
                val containerH = with(density) { maxHeight.toPx() }
                val imgAspect = bmp.width.toFloat() / bmp.height.coerceAtLeast(1).toFloat()
                val boxAspect = containerW / containerH.coerceAtLeast(1f)

                val drawW: Float
                val drawH: Float
                if (imgAspect > boxAspect) {
                    drawW = containerW
                    drawH = containerW / imgAspect
                } else {
                    drawH = containerH
                    drawW = containerH * imgAspect
                }
                val imgLeft = (containerW - drawW) / 2f
                val imgTop = (containerH - drawH) / 2f
                val imageBitmap = remember(bmp) { bmp.asImageBitmap() }
                val handleHitPx = with(density) { 28.dp.toPx() }
                val minSpan = 0.10f

                var activeTarget by remember { mutableStateOf(DragTarget.NONE) }

                Canvas(
                    modifier = Modifier
                        .fillMaxSize()
                        .pointerInput(bmp, drawW, drawH) {
                            detectDragGestures(
                                onDragStart = { start ->
                                    val cL = imgLeft + leftF * drawW
                                    val cT = imgTop + topF * drawH
                                    val cR = imgLeft + rightF * drawW
                                    val cB = imgTop + bottomF * drawH

                                    val corners = listOf(
                                        DragTarget.TOP_LEFT to Offset(cL, cT),
                                        DragTarget.TOP_RIGHT to Offset(cR, cT),
                                        DragTarget.BOTTOM_LEFT to Offset(cL, cB),
                                        DragTarget.BOTTOM_RIGHT to Offset(cR, cB)
                                    )
                                    val nearestCorner = corners.minByOrNull { hypot(start.x - it.second.x, start.y - it.second.y) }
                                    activeTarget = when {
                                        nearestCorner != null && hypot(start.x - nearestCorner.second.x, start.y - nearestCorner.second.y) <= handleHitPx ->
                                            nearestCorner.first
                                        abs(start.x - cL) <= handleHitPx * 0.7f && start.y in cT..cB -> DragTarget.LEFT_EDGE
                                        abs(start.x - cR) <= handleHitPx * 0.7f && start.y in cT..cB -> DragTarget.RIGHT_EDGE
                                        abs(start.y - cT) <= handleHitPx * 0.7f && start.x in cL..cR -> DragTarget.TOP_EDGE
                                        abs(start.y - cB) <= handleHitPx * 0.7f && start.x in cL..cR -> DragTarget.BOTTOM_EDGE
                                        start.x in cL..cR && start.y in cT..cB -> DragTarget.MOVE_BOX
                                        else -> DragTarget.NONE
                                    }
                                },
                                onDragEnd = { activeTarget = DragTarget.NONE },
                                onDragCancel = { activeTarget = DragTarget.NONE },
                                onDrag = { change, dragAmount ->
                                    change.consume()
                                    val dx = dragAmount.x / drawW.coerceAtLeast(1f)
                                    val dy = dragAmount.y / drawH.coerceAtLeast(1f)
                                    when (activeTarget) {
                                        DragTarget.TOP_LEFT -> {
                                            leftF = (leftF + dx).coerceIn(0f, rightF - minSpan)
                                            topF = (topF + dy).coerceIn(0f, bottomF - minSpan)
                                        }
                                        DragTarget.TOP_RIGHT -> {
                                            rightF = (rightF + dx).coerceIn(leftF + minSpan, 1f)
                                            topF = (topF + dy).coerceIn(0f, bottomF - minSpan)
                                        }
                                        DragTarget.BOTTOM_LEFT -> {
                                            leftF = (leftF + dx).coerceIn(0f, rightF - minSpan)
                                            bottomF = (bottomF + dy).coerceIn(topF + minSpan, 1f)
                                        }
                                        DragTarget.BOTTOM_RIGHT -> {
                                            rightF = (rightF + dx).coerceIn(leftF + minSpan, 1f)
                                            bottomF = (bottomF + dy).coerceIn(topF + minSpan, 1f)
                                        }
                                        DragTarget.LEFT_EDGE -> leftF = (leftF + dx).coerceIn(0f, rightF - minSpan)
                                        DragTarget.RIGHT_EDGE -> rightF = (rightF + dx).coerceIn(leftF + minSpan, 1f)
                                        DragTarget.TOP_EDGE -> topF = (topF + dy).coerceIn(0f, bottomF - minSpan)
                                        DragTarget.BOTTOM_EDGE -> bottomF = (bottomF + dy).coerceIn(topF + minSpan, 1f)
                                        DragTarget.MOVE_BOX -> {
                                            val wSpan = rightF - leftF
                                            val hSpan = bottomF - topF
                                            val nextL = (leftF + dx).coerceIn(0f, 1f - wSpan)
                                            val nextT = (topF + dy).coerceIn(0f, 1f - hSpan)
                                            leftF = nextL
                                            rightF = nextL + wSpan
                                            topF = nextT
                                            bottomF = nextT + hSpan
                                        }
                                        DragTarget.NONE -> Unit
                                    }
                                }
                            )
                        }
                ) {
                    drawImage(
                        image = imageBitmap,
                        dstOffset = IntOffset(imgLeft.roundToInt(), imgTop.roundToInt()),
                        dstSize = IntSize(drawW.roundToInt(), drawH.roundToInt())
                    )

                    val cropRect = Rect(
                        left = imgLeft + leftF * drawW,
                        top = imgTop + topF * drawH,
                        right = imgLeft + rightF * drawW,
                        bottom = imgTop + bottomF * drawH
                    )

                    // Máscara escura fora da área selecionada
                    val dim = Color.Black.copy(alpha = 0.62f)
                    drawRect(dim, Offset(imgLeft, imgTop), Size(drawW, (cropRect.top - imgTop).coerceAtLeast(0f)))
                    drawRect(dim, Offset(imgLeft, cropRect.bottom), Size(drawW, (imgTop + drawH - cropRect.bottom).coerceAtLeast(0f)))
                    drawRect(dim, Offset(imgLeft, cropRect.top), Size((cropRect.left - imgLeft).coerceAtLeast(0f), cropRect.height))
                    drawRect(dim, Offset(cropRect.right, cropRect.top), Size((imgLeft + drawW - cropRect.right).coerceAtLeast(0f), cropRect.height))

                    // Borda e grade de terços dentro do recorte
                    drawRect(
                        color = AuraCyan,
                        topLeft = cropRect.topLeft,
                        size = cropRect.size,
                        style = Stroke(width = 2.dp.toPx())
                    )
                    val thirdW = cropRect.width / 3f
                    val thirdH = cropRect.height / 3f
                    val gridColor = AuraCyan.copy(alpha = 0.28f)
                    for (i in 1..2) {
                        drawLine(gridColor, Offset(cropRect.left + thirdW * i, cropRect.top), Offset(cropRect.left + thirdW * i, cropRect.bottom), strokeWidth = 1.dp.toPx())
                        drawLine(gridColor, Offset(cropRect.left, cropRect.top + thirdH * i), Offset(cropRect.right, cropRect.top + thirdH * i), strokeWidth = 1.dp.toPx())
                    }

                    // Alças L brilhantes nos 4 cantos
                    val arm = 16.dp.toPx()
                    val strokeW = 3.5.dp.toPx()
                    val handleColor = AuraEmerald
                    // Top-Left
                    drawLine(handleColor, cropRect.topLeft, Offset(cropRect.left + arm, cropRect.top), strokeW)
                    drawLine(handleColor, cropRect.topLeft, Offset(cropRect.left, cropRect.top + arm), strokeW)
                    // Top-Right
                    drawLine(handleColor, cropRect.topRight, Offset(cropRect.right - arm, cropRect.top), strokeW)
                    drawLine(handleColor, cropRect.topRight, Offset(cropRect.right, cropRect.top + arm), strokeW)
                    // Bottom-Left
                    drawLine(handleColor, cropRect.bottomLeft, Offset(cropRect.left + arm, cropRect.bottom), strokeW)
                    drawLine(handleColor, cropRect.bottomLeft, Offset(cropRect.left, cropRect.bottom - arm), strokeW)
                    // Bottom-Right
                    drawLine(handleColor, cropRect.bottomRight, Offset(cropRect.right - arm, cropRect.bottom), strokeW)
                    drawLine(handleColor, cropRect.bottomRight, Offset(cropRect.right, cropRect.bottom - arm), strokeW)
                }
            }
        }

        Spacer(Modifier.height(10.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            AuraGhostButton(
                text = "Tela Cheia",
                onClick = {
                    leftF = 0f
                    topF = 0f
                    rightF = 1f
                    bottomF = 1f
                },
                modifier = Modifier.weight(1f),
                tint = TextSecondary
            )
            AuraGhostButton(
                text = "Cancelar",
                onClick = onCancel,
                modifier = Modifier.weight(1f),
                tint = TextMuted
            )
        }

        Spacer(Modifier.height(10.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            AuraGhostButton(
                text = "Usar Inteira",
                onClick = { exportAndScan(fullImage = true) },
                modifier = Modifier.weight(1f),
                tint = AuraCyan
            )
            AuraGradientButton(
                text = if (isSavingCrop) "Recortando..." else "Recortar e Ler",
                icon = if (isSavingCrop) Icons.Rounded.Check else Icons.Rounded.Crop,
                onClick = { if (!isSavingCrop && displayBitmap != null) exportAndScan(fullImage = false) },
                modifier = Modifier.weight(1.3f)
            )
        }
    }
}

private fun loadUprightBitmap(context: Context, uri: Uri, maxEdge: Int): Bitmap? {
    return runCatching {
        val resolver = context.contentResolver
        val orientation = resolver.openInputStream(uri)?.use { stream ->
            ExifInterface(stream).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
        } ?: ExifInterface.ORIENTATION_NORMAL

        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        val maxDim = maxOf(bounds.outWidth, bounds.outHeight).coerceAtLeast(1)
        var sample = 1
        while (maxDim / sample > maxEdge) sample *= 2

        val opts = BitmapFactory.Options().apply { inSampleSize = sample }
        val raw = resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) } ?: return null

        val matrix = Matrix()
        when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
            ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
            ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
            ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.preScale(-1f, 1f)
            ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.preScale(1f, -1f)
            ExifInterface.ORIENTATION_TRANSPOSE -> {
                matrix.postRotate(90f)
                matrix.preScale(-1f, 1f)
            }
            ExifInterface.ORIENTATION_TRANSVERSE -> {
                matrix.postRotate(270f)
                matrix.preScale(-1f, 1f)
            }
            else -> return raw
        }
        val rotated = Bitmap.createBitmap(raw, 0, 0, raw.width, raw.height, matrix, true)
        if (rotated !== raw) raw.recycle()
        rotated
    }.getOrNull()
}

private fun rotateBitmap(source: Bitmap, degrees: Float): Bitmap {
    if (degrees % 360f == 0f) return source
    val matrix = Matrix().apply { postRotate(degrees) }
    return Bitmap.createBitmap(source, 0, 0, source.width, source.height, matrix, true)
}
