package com.example.aurapostoassitance.data.vision

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.util.Xml
import com.example.aurapostoassitance.data.local.ServerConfig
import com.example.aurapostoassitance.data.local.memory.AuraSemanticMemoryVault
import com.example.aurapostoassitance.data.npu.AuraNpuEngine
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import org.xmlpull.v1.XmlPullParser
import java.io.File
import java.io.FileOutputStream
import java.io.StringReader
import java.text.NumberFormat
import java.util.Locale
import java.util.regex.Pattern
import javax.inject.Inject
import javax.inject.Singleton

enum class ScannedDocType(val label: String) {
    DANFE_NOTA_FISCAL("Nota Fiscal (DANFE)"),
    MEDICAO_TANQUE("Medição de Tanques (Veeder-Root)"),
    FECHAMENTO_CAIXA("Fechamento de Turno / Caixa"),
    PRECO_CONCORRENCIA("Placa de Preço / Concorrência"),
    DOCUMENTO_GERAL("Documento Geral")
}

data class ScannedDocumentTelemetry(
    val docType: ScannedDocType,
    val title: String,
    val rawText: String,
    val cnpjs: List<String>,
    val currencyValues: List<Double>,
    val totalEstimatedValue: Double?,
    val volumeLiterValues: List<Double>,
    val totalVolumeLiters: Double?,
    val detectedFuels: List<String>,
    val detectedDates: List<String>,
    val executiveSummary: String,
    val promptForAura: String,
    val scanLatencyMs: Long,
    val hardwareAccelerated: Boolean,
    val accessKey: String? = null,
    val accessKeyVerified: Boolean = false,
    val nfeNumber: String? = null,
    val qrCodeUrl: String? = null,
    val sourceFormat: String = "Imagem",
    val previewImagePath: String? = null,
    val compactHighlights: String = ""
)

private data class BarcodeExtraction(
    val accessKey: String? = null,
    val accessKeyVerified: Boolean = false,
    val qrUrl: String? = null,
    val rawValues: List<String> = emptyList(),
    val barcodeSource: String? = null
)

private data class XmlItemRow(
    val name: String,
    val ncm: String = "",
    val cfop: String = "",
    val qty: String = "",
    val unit: String = "",
    val unitPrice: String = "",
    val total: String = ""
)

/**
 * Scanner Neural On-Device acelerado pela Hexagon NPU / Adreno GPU via ML Kit Vision (OCR + Código de Barras/QR),
 * além de leitor nativo de PDF (PdfRenderer) e XML NF-e/NFC-e (XmlPullParser).
 */
@Singleton
class AuraVisionNpuScanner @Inject constructor(
    @param:ApplicationContext private val context: Context,
    private val npuEngine: AuraNpuEngine,
    private val memoryVault: AuraSemanticMemoryVault,
    private val serverConfig: ServerConfig
) {

    private val recognizer by lazy {
        TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    }
    private val barcodeScanner by lazy {
        BarcodeScanning.getClient(
            BarcodeScannerOptions.Builder()
                .setBarcodeFormats(
                    Barcode.FORMAT_CODE_128,
                    Barcode.FORMAT_ITF,
                    Barcode.FORMAT_QR_CODE,
                    Barcode.FORMAT_PDF417,
                    Barcode.FORMAT_DATA_MATRIX
                )
                .build()
        )
    }

    private val cnpjPattern = Pattern.compile("\\b\\d{2}\\.?\\d{3}\\.?\\d{3}/?\\d{4}-?\\d{2}\\b")
    private val currencyPattern = Pattern.compile("(?:R\\$\\s*|TOTAL[:\\s]*R?\\$?)([\\d]{1,3}(?:\\.[\\d]{3})*,[\\d]{2})", Pattern.CASE_INSENSITIVE)
    private val generalNumberPattern = Pattern.compile("([\\d]{1,3}(?:\\.[\\d]{3})*,[\\d]{2})")
    private val volumePattern = Pattern.compile("([\\d]{1,3}(?:\\.[\\d]{3})*(?:,[\\d]{1,3})?)\\s*(?:litros?|L\\b|m³|m3)", Pattern.CASE_INSENSITIVE)
    private val datePattern = Pattern.compile("\\b(\\d{2}/\\d{2}/\\d{4}|\\d{2}-\\d{2}-\\d{4})\\b")
    private val accessKeySpacedPattern = Pattern.compile("(?:\\d[\\s.\\-]*){44}")
    private val plain44Pattern = Pattern.compile("(?<!\\d)(\\d{44})(?!\\d)")

    private val fuelKeywords = listOf(
        "GASOLINA COMUM", "GASOLINA ADITIVADA", "ETANOL", "DIESEL S10", "DIESEL S-10",
        "DIESEL S500", "DIESEL S-500", "ARLA 32", "GNV", "LUBRIFICANTE", "OLEO 15W40"
    )

    suspend fun scanBitmap(bitmap: Bitmap): ScannedDocumentTelemetry = withContext(Dispatchers.Default) {
        val start = System.currentTimeMillis()
        val image = InputImage.fromBitmap(bitmap, 0)
        val (text, barcodeInfo) = runOcrAndBarcodes(image)
        val previewPath = saveBitmapPreview(bitmap, "scan_preview_${System.currentTimeMillis()}.jpg")
        val latency = System.currentTimeMillis() - start

        parseOperationalDocument(
            rawText = text,
            latencyMs = latency,
            barcodeInfo = barcodeInfo,
            sourceFormat = "Imagem (Câmera/NPU)",
            previewImagePath = previewPath
        )
    }

    suspend fun scanUri(uri: Uri): ScannedDocumentTelemetry = withContext(Dispatchers.IO) {
        val start = System.currentTimeMillis()
        val mime = (context.contentResolver.getType(uri) ?: "").lowercase(Locale.ROOT)
        val uriStr = (uri.lastPathSegment ?: uri.toString()).lowercase(Locale.ROOT)
        val header = readHeaderSnippet(uri)

        val isXml = mime.contains("xml") ||
            uriStr.endsWith(".xml") ||
            header.startsWith("<?xml") ||
            header.contains("<nfeProc") ||
            header.contains("<NFe") ||
            header.contains("<infNFe")

        val isPdf = mime == "application/pdf" ||
            uriStr.endsWith(".pdf") ||
            header.startsWith("%PDF-")

        when {
            isXml -> scanXmlUri(uri, start)
            isPdf -> scanPdfUri(uri, start)
            else -> scanImageUri(uri, start)
        }
    }

    private suspend fun scanImageUri(uri: Uri, startTimeMs: Long): ScannedDocumentTelemetry {
        val decoded = decodeDownsampledBitmap(uri, maxEdge = 1920)
        val (text, barcodeInfo, previewPath) = if (decoded != null) {
            try {
                val image = InputImage.fromBitmap(decoded, 0)
                val (ocrText, barcodes) = runOcrAndBarcodes(image)
                val preview = saveBitmapPreview(decoded, "img_preview_${System.currentTimeMillis()}.jpg")
                Triple(ocrText, barcodes, preview)
            } finally {
                decoded.recycle()
            }
        } else {
            val image = InputImage.fromFilePath(context, uri)
            val (ocrText, barcodes) = runOcrAndBarcodes(image)
            val preview = saveUriImagePreview(uri)
            Triple(ocrText, barcodes, preview)
        }
        val latency = System.currentTimeMillis() - startTimeMs

        return parseOperationalDocument(
            rawText = text,
            latencyMs = latency,
            barcodeInfo = barcodeInfo,
            sourceFormat = "Imagem (ML Kit + Código de Barras)",
            previewImagePath = previewPath
        )
    }

    private fun decodeDownsampledBitmap(uri: Uri, maxEdge: Int): Bitmap? {
        return runCatching {
            val resolver = context.contentResolver
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
            val maxDim = maxOf(bounds.outWidth, bounds.outHeight)
            var sample = 1
            while (maxDim / sample > maxEdge) sample *= 2
            val opts = BitmapFactory.Options().apply {
                inSampleSize = sample
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }
            resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) }
        }.getOrNull()
    }

    private suspend fun scanPdfUri(uri: Uri, startTimeMs: Long): ScannedDocumentTelemetry {
        val pfd: ParcelFileDescriptor = context.contentResolver.openFileDescriptor(uri, "r")
            ?: throw IllegalStateException("Não foi possível abrir o arquivo PDF.")

        val combinedText = StringBuilder()
        var mergedBarcode = BarcodeExtraction()
        var firstPagePreviewPath: String? = null

        pfd.use { descriptor ->
            PdfRenderer(descriptor).use { renderer ->
                val maxPages = minOf(renderer.pageCount, 2)
                for (pageIndex in 0 until maxPages) {
                    renderer.openPage(pageIndex).use { page ->
                        val maxTarget = 1800f
                        val scale = minOf(2.4f, maxTarget / maxOf(page.width, page.height).coerceAtLeast(1))
                        val w = (page.width * scale).toInt().coerceAtLeast(600)
                        val h = (page.height * scale).toInt().coerceAtLeast(800)

                        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                        Canvas(bmp).drawColor(Color.WHITE)
                        page.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)

                        if (pageIndex == 0) {
                            firstPagePreviewPath = saveBitmapPreview(bmp, "pdf_page1_${System.currentTimeMillis()}.jpg")
                        }

                        val image = InputImage.fromBitmap(bmp, 0)
                        val (pageText, pageBarcode) = runOcrAndBarcodes(image)
                        if (pageText.isNotBlank()) {
                            if (combinedText.isNotEmpty()) combinedText.append("\n\n--- Página ${pageIndex + 1} ---\n")
                            combinedText.append(pageText)
                        }
                        if (mergedBarcode.accessKey == null && pageBarcode.accessKey != null) {
                            mergedBarcode = pageBarcode
                        } else if (mergedBarcode.qrUrl == null && pageBarcode.qrUrl != null) {
                            mergedBarcode = mergedBarcode.copy(qrUrl = pageBarcode.qrUrl)
                        }
                        bmp.recycle()
                    }
                }
            }
        }

        val latency = System.currentTimeMillis() - startTimeMs
        return parseOperationalDocument(
            rawText = combinedText.toString(),
            latencyMs = latency,
            barcodeInfo = mergedBarcode,
            sourceFormat = "PDF (Renderizado + Barcode/OCR)",
            previewImagePath = firstPagePreviewPath
        )
    }

    private fun scanXmlUri(uri: Uri, startTimeMs: Long): ScannedDocumentTelemetry {
        val xmlBytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            ?: throw IllegalStateException("Não foi possível ler o arquivo XML.")
        val xmlText = xmlBytes.toString(Charsets.UTF_8)

        var accessKey: String? = null
        var nfeNumber: String? = null
        var serie: String? = null
        var dhEmi: String? = null
        var natOp: String? = null
        var emitCnpj: String? = null
        var emitName: String? = null
        var destCnpj: String? = null
        var destName: String? = null
        var vProd: Double? = null
        var vDesc: Double? = null
        var vIcms: Double? = null
        var vSt: Double? = null
        var vNf: Double? = null

        val items = mutableListOf<XmlItemRow>()
        val parser = Xml.newPullParser()
        parser.setFeature(XmlPullParser.FEATURE_PROCESS_NAMESPACES, false)
        parser.setInput(StringReader(xmlText))

        var currentSection = ""
        var currentTag = ""
        var inDet = false
        var itemName = ""
        var itemNcm = ""
        var itemCfop = ""
        var itemQty = ""
        var itemUnit = ""
        var itemUnitPrice = ""
        var itemTotal = ""

        var eventType = parser.eventType
        while (eventType != XmlPullParser.END_DOCUMENT) {
            when (eventType) {
                XmlPullParser.START_TAG -> {
                    currentTag = parser.name ?: ""
                    when (currentTag) {
                        "infNFe" -> {
                            val idAttr = parser.getAttributeValue(null, "Id") ?: ""
                            val digits = idAttr.filter { it.isDigit() }
                            if (digits.length == 44) accessKey = digits
                        }
                        "emit", "dest", "ide", "ICMSTot" -> currentSection = currentTag
                        "det" -> {
                            inDet = true
                            currentSection = "det"
                            itemName = ""
                            itemNcm = ""
                            itemCfop = ""
                            itemQty = ""
                            itemUnit = ""
                            itemUnitPrice = ""
                            itemTotal = ""
                        }
                    }
                }
                XmlPullParser.TEXT -> {
                    val textVal = parser.text?.trim().orEmpty()
                    if (textVal.isNotEmpty()) {
                        when {
                            currentTag == "chNFe" && textVal.filter { it.isDigit() }.length == 44 ->
                                accessKey = textVal.filter { it.isDigit() }
                            currentSection == "ide" && currentTag == "nNF" -> nfeNumber = textVal
                            currentSection == "ide" && currentTag == "serie" -> serie = textVal
                            currentSection == "ide" && currentTag == "dhEmi" -> dhEmi = textVal
                            currentSection == "ide" && currentTag == "natOp" -> natOp = textVal
                            currentSection == "emit" && currentTag == "CNPJ" -> emitCnpj = formatCnpj(textVal)
                            currentSection == "emit" && currentTag == "xNome" -> emitName = textVal
                            currentSection == "dest" && currentTag == "CNPJ" -> destCnpj = formatCnpj(textVal)
                            currentSection == "dest" && currentTag == "xNome" -> destName = textVal
                            currentSection == "ICMSTot" && currentTag == "vProd" -> vProd = textVal.toDoubleOrNull()
                            currentSection == "ICMSTot" && currentTag == "vDesc" -> vDesc = textVal.toDoubleOrNull()
                            currentSection == "ICMSTot" && currentTag == "vICMS" -> vIcms = textVal.toDoubleOrNull()
                            currentSection == "ICMSTot" && currentTag == "vST" -> vSt = textVal.toDoubleOrNull()
                            currentSection == "ICMSTot" && currentTag == "vNF" -> vNf = textVal.toDoubleOrNull()
                            inDet && currentTag == "xProd" -> itemName = textVal
                            inDet && currentTag == "NCM" -> itemNcm = textVal
                            inDet && currentTag == "CFOP" -> itemCfop = textVal
                            inDet && currentTag == "qCom" -> itemQty = textVal
                            inDet && currentTag == "uCom" -> itemUnit = textVal
                            inDet && currentTag == "vUnCom" -> itemUnitPrice = textVal
                            inDet && currentTag == "vProd" -> itemTotal = textVal
                        }
                    }
                }
                XmlPullParser.END_TAG -> {
                    when (parser.name) {
                        "det" -> {
                            if (inDet && itemName.isNotBlank() && items.size < 25) {
                                items.add(XmlItemRow(itemName, itemNcm, itemCfop, itemQty, itemUnit, itemUnitPrice, itemTotal))
                            }
                            inDet = false
                            currentSection = ""
                        }
                        "emit", "dest", "ide", "ICMSTot" -> currentSection = ""
                    }
                    currentTag = ""
                }
            }
            eventType = parser.next()
        }

        val cnpjs = listOfNotNull(emitCnpj, destCnpj).distinct()
        val currencyValues = listOfNotNull(vNf, vProd, vIcms, vSt, vDesc).filter { it > 0.0 }
        val ptBr = NumberFormat.getCurrencyInstance(Locale("pt", "BR"))
        val verified = accessKey != null && isValidNfeAccessKey(accessKey)
        val detectedDate = dhEmi?.take(10)?.split("-")?.let {
            if (it.size == 3) listOf("${it[2]}/${it[1]}/${it[0]}") else emptyList()
        } ?: emptyList()

        val rawText = buildString {
            append("XML NF-e Oficial (Precisão 100%)\n")
            if (nfeNumber != null) append("NF-e nº $nfeNumber (Série ${serie ?: "1"})\n")
            if (accessKey != null) append("Chave de Acesso: $accessKey\n")
            if (!natOp.isNullOrBlank()) append("Natureza: $natOp\n")
            if (!emitName.isNullOrBlank()) append("Emitente: $emitName (${emitCnpj ?: ""})\n")
            if (!destName.isNullOrBlank()) append("Destinatário: $destName (${destCnpj ?: ""})\n")
            if (detectedDate.isNotEmpty()) append("Emissão: ${detectedDate.first()}\n")
            append("Totais XML: Produtos=${vProd?.let { ptBr.format(it) } ?: "N/D"} | Desconto=${vDesc?.let { ptBr.format(it) } ?: "R$ 0,00"} | ICMS=${vIcms?.let { ptBr.format(it) } ?: "N/D"} | ICMS-ST=${vSt?.let { ptBr.format(it) } ?: "N/D"} | Total NF=${vNf?.let { ptBr.format(it) } ?: "N/D"}\n")
            if (items.isNotEmpty()) {
                append("\nItens do XML (${items.size}):\n")
                items.forEachIndexed { idx, row ->
                    append("${idx + 1}. ${row.name} | NCM=${row.ncm} | CFOP=${row.cfop} | Qtd=${row.qty} ${row.unit} | Unit=${row.unitPrice} | Total=${row.total}\n")
                }
            }
        }.trim()

        val title = buildString {
            append("XML NF-e")
            if (!nfeNumber.isNullOrBlank()) append(" nº $nfeNumber") else append(" Auditado")
        }

        val executiveSummary = buildString {
            append("• Fonte: XML Fiscal Oficial (Zero erro de OCR)\n")
            if (!emitName.isNullOrBlank()) append("• Emitente: $emitName\n")
            if (cnpjs.isNotEmpty()) append("• CNPJ(s): ${cnpjs.joinToString(", ")}\n")
            if (vNf != null) append("• Valor Total NF-e: ${ptBr.format(vNf)}\n")
            if (accessKey != null) append("• Chave 44 dígitos: ${formatAccessKeyGrouped(accessKey)}${if (verified) " (DV ✓)" else ""}\n")
            append("• Itens extraídos: ${items.size}\n")
            if (detectedDate.isNotEmpty()) append("• Emissão: ${detectedDate.first()}")
        }.trim()

        val highlights = buildList {
            if (!nfeNumber.isNullOrBlank()) add("NF nº $nfeNumber")
            if (vNf != null) add(ptBr.format(vNf))
            if (!emitCnpj.isNullOrBlank()) add("CNPJ $emitCnpj")
            add("${items.size} item(ns) no XML")
        }.joinToString(" • ")

        val cleanXmlForAudit = extractCleanXmlForAudit(xmlText)
        val promptForAura = buildString {
            append("Audite este arquivo XML oficial de NF-e/NFC-e (valide totais W07-10/vProd vs soma dos itens, NCM/CFOP, alíquotas ICMS/ST e divergências fiscais):\n\n")
            append(rawText.take(2200))
            if (cleanXmlForAudit.isNotBlank()) {
                append("\n\n")
                append(cleanXmlForAudit)
            }
        }

        val allUpper = rawText.uppercase(Locale.getDefault())
        val fuels = fuelKeywords.filter { allUpper.contains(it) }
        val latency = System.currentTimeMillis() - startTimeMs

        return ScannedDocumentTelemetry(
            docType = ScannedDocType.DANFE_NOTA_FISCAL,
            title = title,
            rawText = rawText,
            cnpjs = cnpjs,
            currencyValues = currencyValues,
            totalEstimatedValue = vNf ?: vProd,
            volumeLiterValues = emptyList(),
            totalVolumeLiters = null,
            detectedFuels = fuels,
            detectedDates = detectedDate,
            executiveSummary = executiveSummary,
            promptForAura = promptForAura,
            scanLatencyMs = latency,
            hardwareAccelerated = true,
            accessKey = accessKey,
            accessKeyVerified = verified,
            nfeNumber = nfeNumber,
            qrCodeUrl = null,
            sourceFormat = "XML NF-e Oficial",
            previewImagePath = null,
            compactHighlights = highlights
        )
    }

    private fun extractCleanXmlForAudit(rawXml: String): String {
        val noSig = rawXml.replace(Regex("<Signature[\\s\\S]*?</Signature>", RegexOption.IGNORE_CASE), "").trim()
        val infStart = noSig.indexOf("<infNFe")
        val infEnd = noSig.lastIndexOf("</infNFe>")
        if (infStart >= 0 && infEnd > infStart) {
            val infSlice = noSig.substring(infStart, infEnd + "</infNFe>".length)
            val wrapped = "<NFe>$infSlice</NFe>"
            if (wrapped.length <= 6000) return wrapped
        }
        return if (noSig.length <= 6000) noSig else ""
    }

    private suspend fun runOcrAndBarcodes(image: InputImage): Pair<String, BarcodeExtraction> = coroutineScope {
        val textDeferred = async {
            runCatching { recognizer.process(image).await().text }.getOrDefault("")
        }
        val barcodeDeferred = async {
            runCatching {
                val barcodes = barcodeScanner.process(image).await()
                extractBarcodeMetadata(barcodes)
            }.getOrDefault(BarcodeExtraction())
        }
        textDeferred.await() to barcodeDeferred.await()
    }

    private fun extractBarcodeMetadata(barcodes: List<Barcode>): BarcodeExtraction {
        if (barcodes.isEmpty()) return BarcodeExtraction()
        val rawList = mutableListOf<String>()
        var foundKey: String? = null
        var keyVerified = false
        var qrUrl: String? = null
        var sourceLabel: String? = null

        for (barcode in barcodes) {
            val raw = barcode.rawValue?.trim().orEmpty()
            if (raw.isEmpty()) continue
            rawList.add(raw)

            if (barcode.format == Barcode.FORMAT_QR_CODE && (raw.startsWith("http", ignoreCase = true) || raw.contains("sefaz", ignoreCase = true))) {
                qrUrl = raw
            }

            val urlKey = Regex("chNFe=(\\d{44})|p=(\\d{44})", RegexOption.IGNORE_CASE).find(raw)
                ?.groupValues?.drop(1)?.firstOrNull { it.length == 44 }
            val matcher44 = plain44Pattern.matcher(raw.replace(" ", ""))
            val candidate = urlKey ?: if (matcher44.find()) matcher44.group(1) else null

            if (candidate != null && candidate.length == 44) {
                val valid = isValidNfeAccessKey(candidate)
                if (foundKey == null || (!keyVerified && valid)) {
                    foundKey = candidate
                    keyVerified = valid
                    sourceLabel = if (barcode.format == Barcode.FORMAT_QR_CODE) "QR Code NFC-e" else "Código de Barras DANFE"
                }
            }
        }

        return BarcodeExtraction(
            accessKey = foundKey,
            accessKeyVerified = keyVerified,
            qrUrl = qrUrl,
            rawValues = rawList.distinct(),
            barcodeSource = sourceLabel
        )
    }

    private fun parseOperationalDocument(
        rawText: String,
        latencyMs: Long,
        barcodeInfo: BarcodeExtraction = BarcodeExtraction(),
        sourceFormat: String = "Imagem",
        previewImagePath: String? = null
    ): ScannedDocumentTelemetry {
        val trimmedText = rawText.trim()
        val enrichedText = buildString {
            if (trimmedText.isNotEmpty()) append(trimmedText)
            if (barcodeInfo.accessKey != null && !trimmedText.contains(barcodeInfo.accessKey)) {
                if (isNotEmpty()) append("\n")
                append("CHAVE DE ACESSO LIDA NO CÓDIGO DE BARRAS: ${barcodeInfo.accessKey}")
            }
            if (!barcodeInfo.qrUrl.isNullOrBlank()) {
                if (isNotEmpty()) append("\n")
                append("QR CODE SEFAZ: ${barcodeInfo.qrUrl}")
            }
        }.trim()

        val upperText = enrichedText.uppercase(Locale.getDefault())

        // 0. Extração e validação da Chave de Acesso de 44 dígitos (Barcode tem prioridade; fallback OCR)
        var accessKey = barcodeInfo.accessKey
        var accessKeyVerified = barcodeInfo.accessKeyVerified
        var keySource = barcodeInfo.barcodeSource

        if (accessKey == null) {
            val spacedMatcher = accessKeySpacedPattern.matcher(enrichedText)
            while (spacedMatcher.find()) {
                val digits = spacedMatcher.group().filter { it.isDigit() }
                if (digits.length == 44) {
                    val valid = isValidNfeAccessKey(digits)
                    if (accessKey == null || (!accessKeyVerified && valid)) {
                        accessKey = digits
                        accessKeyVerified = valid
                        keySource = "OCR NPU"
                    }
                    if (valid) break
                }
            }
        }

        val keyMeta = accessKey?.let { decodeAccessKeyInfo(it) }
        val nfeNumber = keyMeta?.numero

        // 1. Classificação do tipo de documento
        val docType = when {
            accessKey != null ||
                upperText.contains("DANFE") || upperText.contains("DOCUMENTO AUXILIAR") ||
                upperText.contains("CHAVE DE ACESSO") || upperText.contains("NOTA FISCAL") ||
                upperText.contains("NF-E") || upperText.contains("NFC-E") ||
                upperText.contains("CUPOM FISCAL") || upperText.contains("CFOP") ||
                upperText.contains("ICMS") || upperText.contains("EMITENTE") ->
                ScannedDocType.DANFE_NOTA_FISCAL

            upperText.contains("VEEDER") || upperText.contains("SONDA") ||
                upperText.contains("COMPARTIMENTO") || upperText.contains("ESTOQUE FISICO") ||
                upperText.contains("MEDICAO DE TANQUE") ->
                ScannedDocType.MEDICAO_TANQUE

            upperText.contains("FECHAMENTO") || upperText.contains("LMC") ||
                upperText.contains("SANGRIA") || upperText.contains("TURNO") ||
                upperText.contains("CONCILIACAO") ->
                ScannedDocType.FECHAMENTO_CAIXA

            upperText.contains("POSTO") && (upperText.contains("PRECO") || upperText.contains("R$/L") || upperText.contains("BOMBA")) ->
                ScannedDocType.PRECO_CONCORRENCIA

            else -> ScannedDocType.DOCUMENTO_GERAL
        }

        // 2. Extração de CNPJs (inclui CNPJ embutido na chave de 44 dígitos se não houver no OCR)
        val cnpjs = mutableListOf<String>()
        val cnpjMatcher = cnpjPattern.matcher(enrichedText)
        while (cnpjMatcher.find()) {
            val cnpj = cnpjMatcher.group()
            if (!cnpjs.contains(cnpj)) cnpjs.add(cnpj)
        }
        if (keyMeta != null && cnpjs.none { it.filter { ch -> ch.isDigit() } == keyMeta.cnpjDigits }) {
            cnpjs.add(formatCnpj(keyMeta.cnpjDigits))
        }

        // 3. Extração de Valores Monetários
        val currencyValues = mutableListOf<Double>()
        val currencyMatcher = currencyPattern.matcher(enrichedText)
        while (currencyMatcher.find()) {
            val numStr = currencyMatcher.group(1)?.replace(".", "")?.replace(",", ".")
            numStr?.toDoubleOrNull()?.let { if (!currencyValues.contains(it)) currencyValues.add(it) }
        }
        if (currencyValues.isEmpty()) {
            val genMatcher = generalNumberPattern.matcher(enrichedText)
            while (genMatcher.find()) {
                val numStr = genMatcher.group(1)?.replace(".", "")?.replace(",", ".")
                val d = numStr?.toDoubleOrNull()
                if (d != null && d > 10.0 && !currencyValues.contains(d)) {
                    currencyValues.add(d)
                }
            }
        }
        val maxCurrency = currencyValues.maxOrNull()

        // 4. Extração de Volumes em Litros
        val volumeValues = mutableListOf<Double>()
        val volMatcher = volumePattern.matcher(enrichedText)
        while (volMatcher.find()) {
            val volStr = volMatcher.group(1)?.replace(".", "")?.replace(",", ".")
            volStr?.toDoubleOrNull()?.let { if (!volumeValues.contains(it)) volumeValues.add(it) }
        }
        val totalVolume = volumeValues.maxOrNull()

        // 5. Extração de Combustíveis e Produtos
        val detectedFuels = fuelKeywords.filter { upperText.contains(it) }

        // 6. Extração de Datas
        val detectedDates = mutableListOf<String>()
        val dateMatcher = datePattern.matcher(enrichedText)
        while (dateMatcher.find()) {
            val d = dateMatcher.group()
            if (!detectedDates.contains(d)) detectedDates.add(d)
        }

        // 7. Síntese do Resumo Executivo e Prompt para AURA
        val ptBrFormat = NumberFormat.getCurrencyInstance(Locale("pt", "BR"))
        val title = when (docType) {
            ScannedDocType.DANFE_NOTA_FISCAL ->
                if (!nfeNumber.isNullOrBlank()) "DANFE ${keyMeta?.modeloLabel ?: "NF-e"} nº $nfeNumber" else "Nota Fiscal DANFE Auditada"
            ScannedDocType.MEDICAO_TANQUE -> "Medição Física de Tanques"
            ScannedDocType.FECHAMENTO_CAIXA -> "Conciliação de Fechamento / LMC"
            ScannedDocType.PRECO_CONCORRENCIA -> "Monitoramento de Preço de Pista"
            ScannedDocType.DOCUMENTO_GERAL -> "Documento Operacional Escaneado"
        }

        val executiveSummary = buildString {
            append("• Tipo: ${docType.label} ($sourceFormat)\n")
            if (accessKey != null) {
                val statusDv = if (accessKeyVerified) "DV válido ✓" else "DV não confirmado"
                append("• Chave 44 dígitos (${keySource ?: "NPU"}): ${formatAccessKeyGrouped(accessKey)} [$statusDv]\n")
            }
            if (!nfeNumber.isNullOrBlank()) append("• Documento: ${keyMeta?.modeloLabel ?: "NF"} nº $nfeNumber • Série ${keyMeta?.serie ?: "-"}\n")
            if (cnpjs.isNotEmpty()) append("• CNPJ(s): ${cnpjs.take(2).joinToString(", ")}\n")
            if (maxCurrency != null) append("• Valor Principal: ${ptBrFormat.format(maxCurrency)}\n")
            if (totalVolume != null) append("• Volume Detectado: ${"%,.0f".format(Locale("pt", "BR"), totalVolume)} L\n")
            if (detectedFuels.isNotEmpty()) append("• Produtos: ${detectedFuels.joinToString(", ")}\n")
            if (detectedDates.isNotEmpty()) append("• Data: ${detectedDates.first()}\n")
            append("• Aceleração: ${npuEngine.hardwareStatus.value.delegateType} + ML Kit (${latencyMs}ms)")
        }.trim()

        val compactHighlights = buildList {
            if (!nfeNumber.isNullOrBlank()) add("NF nº $nfeNumber")
            if (accessKey != null) add("Chave 44d" + if (accessKeyVerified) " ✓" else "")
            if (cnpjs.isNotEmpty()) add(cnpjs.first())
            if (maxCurrency != null) add(ptBrFormat.format(maxCurrency))
            if (totalVolume != null) add("${"%,.0f".format(Locale("pt", "BR"), totalVolume)} L")
            if (detectedDates.isNotEmpty()) add(detectedDates.first())
        }.take(4).joinToString(" • ")

        val taskDirective = when (docType) {
            ScannedDocType.DANFE_NOTA_FISCAL ->
                "Analise exclusivamente esta Nota Fiscal / DANFE / Cupom Fiscal (chave 44 dígitos, emitente, CNPJ, produtos, quantidades, valores e tributos). NÃO busque nem misture fechamento de turno; resuma os dados lidos e aponte observações ou divergências."
            ScannedDocType.MEDICAO_TANQUE ->
                "Analise esta medição física de tanques, compare os volumes lidos com a autonomia e destaque qualquer risco de ruptura ou desvio."
            ScannedDocType.FECHAMENTO_CAIXA ->
                "Analise este fechamento de turno/caixa e destaque divergências, quebras ou pontos de atenção."
            ScannedDocType.PRECO_CONCORRENCIA ->
                "Analise esta tabela/placa de preços e compare a competitividade por combustível."
            ScannedDocType.DOCUMENTO_GERAL ->
                "Leia e resuma com objetividade os dados identificados neste documento escaneado (valores, itens, datas e CNPJs). Não acione fechamento de turno se o texto não tratar de turno."
        }

        val safeRawSnippet = enrichedText
            .take(2200)
            .replace("#", "nº")
            .replace("&", "e")
            .replace("?", ".")

        val promptForAura = buildString {
            append("Audite o seguinte documento escaneado na NPU do dispositivo (${docType.label}):\n\n")
            if (accessKey != null) {
                append("Chave de Acesso NF-e/NFC-e (44 dígitos): $accessKey (DV ${if (accessKeyVerified) "válido" else "incerto"})\n")
            }
            append("Resumo dos Dados Extraídos:\n$executiveSummary\n\n")
            append("Texto Lido no Documento:\n\"\"\"\n")
            append(safeRawSnippet)
            append("\n\"\"\"\n")
            append(taskDirective)
        }

        val telemetry = ScannedDocumentTelemetry(
            docType = docType,
            title = title,
            rawText = enrichedText,
            cnpjs = cnpjs,
            currencyValues = currencyValues,
            totalEstimatedValue = maxCurrency,
            volumeLiterValues = volumeValues,
            totalVolumeLiters = totalVolume,
            detectedFuels = detectedFuels,
            detectedDates = detectedDates,
            executiveSummary = executiveSummary,
            promptForAura = promptForAura,
            scanLatencyMs = latencyMs,
            hardwareAccelerated = npuEngine.hardwareStatus.value.isHardwareAccelerated,
            accessKey = accessKey,
            accessKeyVerified = accessKeyVerified,
            nfeNumber = nfeNumber,
            qrCodeUrl = barcodeInfo.qrUrl,
            sourceFormat = sourceFormat,
            previewImagePath = previewImagePath,
            compactHighlights = compactHighlights
        )

        // Auto-indexação no Cofre Semântico RAG On-Device
        runCatching {
            val ragContent = buildString {
                append(docType.label)
                if (compactHighlights.isNotBlank()) append(" • $compactHighlights")
                if (accessKey != null) append(" • Chave: $accessKey")
            }
            memoryVault.indexMemory(
                category = "SCAN_DOCUMENTO",
                title = title,
                content = ragContent,
                segment = serverConfig.activePackId
            )
        }

        return telemetry
    }

    private fun readHeaderSnippet(uri: Uri): String {
        return runCatching {
            context.contentResolver.openInputStream(uri)?.use { stream ->
                val buf = ByteArray(128)
                val read = stream.read(buf)
                if (read > 0) String(buf, 0, read, Charsets.UTF_8).trimStart('\uFEFF', ' ', '\n', '\r', '\t') else ""
            } ?: ""
        }.getOrDefault("")
    }

    private fun saveBitmapPreview(bitmap: Bitmap, fileName: String): String? {
        return runCatching {
            val dir = File(context.cacheDir, "vision_scans").apply { mkdirs() }
            val maxEdge = 960
            val w = bitmap.width
            val h = bitmap.height
            val scaled = if (maxOf(w, h) > maxEdge) {
                val ratio = maxEdge.toFloat() / maxOf(w, h).toFloat()
                Bitmap.createScaledBitmap(
                    bitmap,
                    (w * ratio).toInt().coerceAtLeast(1),
                    (h * ratio).toInt().coerceAtLeast(1),
                    true
                )
            } else {
                bitmap
            }
            val outFile = File(dir, fileName)
            FileOutputStream(outFile).use { fos ->
                scaled.compress(Bitmap.CompressFormat.JPEG, 84, fos)
            }
            if (scaled !== bitmap) scaled.recycle()
            pruneVisionCacheDir(dir, maxFiles = 20)
            outFile.absolutePath
        }.getOrNull()
    }

    private fun pruneVisionCacheDir(dir: File, maxFiles: Int) {
        runCatching {
            val files = dir.listFiles()?.filter { it.isFile } ?: return
            if (files.size > maxFiles) {
                files.sortedBy { it.lastModified() }
                    .take(files.size - maxFiles)
                    .forEach { it.delete() }
            }
        }
    }

    private fun saveUriImagePreview(uri: Uri): String? {
        return runCatching {
            val resolver = context.contentResolver
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
            val maxDim = maxOf(bounds.outWidth, bounds.outHeight).coerceAtLeast(1)
            var sample = 1
            while (maxDim / sample > 1280) sample *= 2
            val opts = BitmapFactory.Options().apply { inSampleSize = sample }
            val bmp = resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) } ?: return null
            val path = saveBitmapPreview(bmp, "img_preview_${System.currentTimeMillis()}.jpg")
            bmp.recycle()
            path
        }.getOrNull()
    }

    private data class NfeKeyMeta(
        val cnpjDigits: String,
        val modelo: String,
        val modeloLabel: String,
        val serie: String,
        val numero: String
    )

    private fun decodeAccessKeyInfo(digits: String): NfeKeyMeta? {
        if (digits.length != 44 || !digits.all { it.isDigit() }) return null
        val cnpj = digits.substring(6, 20)
        val modelo = digits.substring(20, 22)
        val serie = digits.substring(22, 25).trimStart('0').ifEmpty { "0" }
        val numero = digits.substring(25, 34).trimStart('0').ifEmpty { "0" }
        val modeloLabel = when (modelo) {
            "55" -> "NF-e"
            "65" -> "NFC-e"
            "57" -> "CT-e"
            else -> "Doc"
        }
        return NfeKeyMeta(cnpj, modelo, modeloLabel, serie, numero)
    }

    private fun isValidNfeAccessKey(digits: String): Boolean {
        if (digits.length != 44 || !digits.all { it.isDigit() }) return false
        var sum = 0
        var weight = 2
        for (i in 42 downTo 0) {
            sum += (digits[i] - '0') * weight
            weight = if (weight == 9) 2 else weight + 1
        }
        val rem = sum % 11
        val expectedDv = if (rem == 0 || rem == 1) 0 else 11 - rem
        return (digits[43] - '0') == expectedDv
    }

    private fun formatAccessKeyGrouped(digits: String): String {
        return digits.chunked(4).joinToString(" ")
    }

    private fun formatCnpj(rawDigits: String): String {
        val d = rawDigits.filter { it.isDigit() }
        if (d.length != 14) return rawDigits
        return "${d.substring(0, 2)}.${d.substring(2, 5)}.${d.substring(5, 8)}/${d.substring(8, 12)}-${d.substring(12, 14)}"
    }
}
