package com.example.aurapostoassitance.ui.chat

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import com.example.aurapostoassitance.data.audio.AuraVoiceManager
import com.example.aurapostoassitance.data.local.AuraOfflineVault
import com.example.aurapostoassitance.data.local.ChatDao
import com.example.aurapostoassitance.data.local.ChatMessageEntity
import com.example.aurapostoassitance.data.local.ChatSessionEntity
import com.example.aurapostoassitance.data.local.HandoffContact
import com.example.aurapostoassitance.data.local.ServerConfig
import com.example.aurapostoassitance.data.local.memory.AuraSemanticMemoryVault
import com.example.aurapostoassitance.data.npu.AuraNpuEngine
import com.example.aurapostoassitance.data.remote.AuraApiService
import com.example.aurapostoassitance.data.remote.HandoffRequest
import com.example.aurapostoassitance.data.remote.HandoffThreadDto
import com.example.aurapostoassitance.data.remote.QuickActionRequest
import com.example.aurapostoassitance.data.remote.SseEvent
import com.example.aurapostoassitance.data.remote.SseRepository
import com.example.aurapostoassitance.data.security.AuraHardwareAuthManager
import com.example.aurapostoassitance.data.vision.AuraSharedIntakeRelay
import com.example.aurapostoassitance.data.vision.AuraVisionNpuScanner
import com.example.aurapostoassitance.data.vision.ScannedDocumentTelemetry
import com.example.aurapostoassitance.ui.genui.GenUiAction
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.onCompletion
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import java.net.ConnectException
import java.net.SocketTimeoutException
import javax.inject.Inject

data class ChatMessage(
    val id: String,
    val text: String,
    val isFromUser: Boolean,
    val isStreaming: Boolean = false,
    /** Envelope GenUI (JSON) para renderizar card nativo abaixo do texto. */
    val envelopeJson: String? = null,
    /** Trilha cronológica das etapas e ferramentas consultadas pela IA. */
    val reasoningSteps: List<String> = emptyList()
)

data class IncomingHandoffAlert(
    val sessionId: String,
    val phone: String,
    val contactName: String,
    val roleLabel: String,
    val previewText: String,
    val unreadCount: Int
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    @param:ApplicationContext private val appContext: Context,
    private val sseRepository: SseRepository,
    private val chatDao: ChatDao,
    private val voiceManager: AuraVoiceManager,
    private val apiService: AuraApiService,
    private val npuEngine: AuraNpuEngine,
    private val offlineVault: AuraOfflineVault,
    private val serverConfig: ServerConfig,
    val hardwareAuthManager: AuraHardwareAuthManager,
    val visionScanner: AuraVisionNpuScanner,
    val memoryVault: AuraSemanticMemoryVault,
    private val sharedIntakeRelay: AuraSharedIntakeRelay
) : ViewModel() {

    // --- Fluxos de Voz e Fala Hands-Free ---
    val isListening: StateFlow<Boolean> = voiceManager.isListening
    val spokenText: StateFlow<String> = voiceManager.spokenText
    val voiceRms: StateFlow<Float> = voiceManager.voiceRms
    val isSpeaking: StateFlow<Boolean> = voiceManager.isSpeaking
    val speakingMessageId: StateFlow<String?> = voiceManager.speakingMessageId
    val voiceError: StateFlow<String?> = voiceManager.voiceError

    private val _isVoiceConversationActive = MutableStateFlow(false)
    val isVoiceConversationActive: StateFlow<Boolean> = _isVoiceConversationActive.asStateFlow()

    private val _openVisionScannerRequest = MutableStateFlow(false)
    val openVisionScannerRequest: StateFlow<Boolean> = _openVisionScannerRequest.asStateFlow()

    private val _currentSessionId = MutableStateFlow("default")
    val currentSessionId: StateFlow<String> = _currentSessionId.asStateFlow()

    private val _currentSessionTitle = MutableStateFlow("AURA")
    val currentSessionTitle: StateFlow<String> = _currentSessionTitle.asStateFlow()

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    private val _sessions = MutableStateFlow<List<ChatSessionEntity>>(emptyList())
    val sessions: StateFlow<List<ChatSessionEntity>> = _sessions.asStateFlow()

    private val _isAuraTyping = MutableStateFlow(false)
    val isAuraTyping: StateFlow<Boolean> = _isAuraTyping.asStateFlow()

    private val _auraStatusMessage = MutableStateFlow<String?>(null)
    val auraStatusMessage: StateFlow<String?> = _auraStatusMessage.asStateFlow()

    private val _handoffContacts = MutableStateFlow(serverConfig.getHandoffContacts())
    val handoffContacts: StateFlow<List<HandoffContact>> = _handoffContacts.asStateFlow()

    private val _lastHandoffRole = MutableStateFlow(serverConfig.lastHandoffRole)
    val lastHandoffRole: StateFlow<String> = _lastHandoffRole.asStateFlow()

    private val _pendingWhatsAppUrl = MutableStateFlow<String?>(null)
    val pendingWhatsAppUrl: StateFlow<String?> = _pendingWhatsAppUrl.asStateFlow()

    private val _hasScannedDocument = MutableStateFlow(false)
    val hasScannedDocument: StateFlow<Boolean> = _hasScannedDocument.asStateFlow()

    private val _lastScannedDocumentTitle = MutableStateFlow<String?>(null)
    val lastScannedDocumentTitle: StateFlow<String?> = _lastScannedDocumentTitle.asStateFlow()

    private val _handoffThreads = MutableStateFlow<List<HandoffThreadDto>>(emptyList())
    val handoffThreads: StateFlow<List<HandoffThreadDto>> = _handoffThreads.asStateFlow()

    private val _totalUnreadHandoffs = MutableStateFlow(0)
    val totalUnreadHandoffs: StateFlow<Int> = _totalUnreadHandoffs.asStateFlow()

    private val _incomingHandoffAlert = MutableStateFlow<IncomingHandoffAlert?>(null)
    val incomingHandoffAlert: StateFlow<IncomingHandoffAlert?> = _incomingHandoffAlert.asStateFlow()

    private val _isWhatsAppReturnsMode = MutableStateFlow(false)
    val isWhatsAppReturnsMode: StateFlow<Boolean> = _isWhatsAppReturnsMode.asStateFlow()

    private val _isViewingWhatsAppContactHub = MutableStateFlow(false)
    val isViewingWhatsAppContactHub: StateFlow<Boolean> = _isViewingWhatsAppContactHub.asStateFlow()

    private val _isSyncingHandoffs = MutableStateFlow(false)
    val isSyncingHandoffs: StateFlow<Boolean> = _isSyncingHandoffs.asStateFlow()

    private val notifiedInboundMessageIds = mutableSetOf<String>()

    private val cachedHandoffDocFile: File
        get() = File(File(appContext.cacheDir, "vision_scans").apply { mkdirs() }, "last_handoff_doc.jpg")

    fun setLastScannedDocument(uri: Uri, title: String) {
        viewModelScope.launch(Dispatchers.IO) {
            runCatching {
                val resolver = appContext.contentResolver
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
                val maxDim = maxOf(bounds.outWidth, bounds.outHeight).coerceAtLeast(1)
                var sample = 1
                while (maxDim / sample > 1600) {
                    sample *= 2
                }
                val opts = BitmapFactory.Options().apply { inSampleSize = sample }
                val decoded = resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) }
                    ?: return@runCatching
                val scaled = scaleDownBitmap(decoded, 1280)
                FileOutputStream(cachedHandoffDocFile).use { out ->
                    scaled.compress(Bitmap.CompressFormat.JPEG, 82, out)
                }
                if (scaled !== decoded) decoded.recycle()
                scaled.recycle()
                _hasScannedDocument.value = true
                _lastScannedDocumentTitle.value = title
            }
        }
    }

    private fun scaleDownBitmap(bitmap: Bitmap, maxEdge: Int): Bitmap {
        val w = bitmap.width
        val h = bitmap.height
        val longest = maxOf(w, h)
        if (longest <= maxEdge) return bitmap
        val ratio = maxEdge.toFloat() / longest.toFloat()
        return Bitmap.createScaledBitmap(bitmap, (w * ratio).toInt().coerceAtLeast(1), (h * ratio).toInt().coerceAtLeast(1), true)
    }

    private suspend fun readCachedAttachmentBase64(): String? = withContext(Dispatchers.IO) {
        runCatching {
            val f = cachedHandoffDocFile
            if (!f.exists() || f.length() == 0L) return@runCatching null
            Base64.encodeToString(f.readBytes(), Base64.NO_WRAP)
        }.getOrNull()
    }

    private suspend fun createPerHandoffSnapshot(normPhone: String, sourcePath: String? = null): String? =
        withContext(Dispatchers.IO) {
            runCatching {
                val srcFile = sourcePath?.let { File(it) }?.takeIf { it.exists() && it.length() > 0L }
                    ?: cachedHandoffDocFile.takeIf { it.exists() && it.length() > 0L }
                    ?: return@runCatching null
                val dir = File(appContext.cacheDir, "vision_scans").apply { mkdirs() }
                val destFile = File(dir, "handoff_${normPhone}_${System.currentTimeMillis()}.jpg")
                srcFile.copyTo(destFile, overwrite = true)
                destFile.absolutePath
            }.getOrNull()
        }

    private suspend fun readPathAsBase64(path: String): String? = withContext(Dispatchers.IO) {
        runCatching {
            val f = File(path)
            if (!f.exists() || f.length() == 0L) return@runCatching null
            Base64.encodeToString(f.readBytes(), Base64.NO_WRAP)
        }.getOrNull()
    }

    fun consumePendingWhatsAppUrl() {
        _pendingWhatsAppUrl.value = null
    }

    fun saveHandoffContact(contact: HandoffContact) {
        serverConfig.saveHandoffContact(contact)
        _handoffContacts.value = serverConfig.getHandoffContacts()
        _lastHandoffRole.value = serverConfig.lastHandoffRole
    }

    fun normalizeWhatsAppPhone(raw: String): String {
        val digits = raw.filter { it.isDigit() }
        return if (digits.length in 10..11 && !digits.startsWith("55")) {
            "55$digits"
        } else {
            digits
        }
    }

    private var messageCollectJob: Job? = null
    private var streamJob: Job? = null

    init {
        viewModelScope.launch {
            chatDao.getAllSessions().collect { sessionList ->
                _sessions.value = sessionList
            }
        }
        viewModelScope.launch {
            sharedIntakeRelay.pendingTelemetry.collect { telemetry ->
                if (telemetry != null && sharedIntakeRelay.consumeTelemetry() != null) {
                    sendScannedDocument(telemetry)
                }
            }
        }
        viewModelScope.launch {
            sharedIntakeRelay.pendingDocument.collect { payload ->
                if (payload != null) {
                    sharedIntakeRelay.markConsumed(payload.id)
                    _auraStatusMessage.value = "Lendo documento recebido (${payload.fileName}) na Hexagon NPU..."
                    runCatching {
                        visionScanner.scanUri(payload.localUri)
                    }.onSuccess { telemetry ->
                        _auraStatusMessage.value = null
                        val attachUri = telemetry.previewImagePath?.let { Uri.fromFile(File(it)) } ?: payload.localUri
                        if (telemetry.previewImagePath != null || payload.mimeType.startsWith("image/")) {
                            setLastScannedDocument(attachUri, telemetry.title)
                        }
                        sendScannedDocument(telemetry)
                    }.onFailure { err ->
                        _auraStatusMessage.value = null
                        val errId = "aura_err_" + System.currentTimeMillis()
                        val msg = ChatMessage(
                            id = errId,
                            text = "Não consegui ler o documento compartilhado (${payload.fileName}): ${err.localizedMessage ?: "formato não suportado"}.",
                            isFromUser = false
                        )
                        _messages.value = _messages.value + msg
                    }
                }
            }
        }
        loadSession("default", "AURA")
        startHandoffPolling()
    }

    private fun startHandoffPolling() {
        viewModelScope.launch {
            kotlinx.coroutines.delay(1500L)
            while (true) {
                refreshHandoffThreads(syncEvolution = true)
                kotlinx.coroutines.delay(8000L)
            }
        }
    }

    fun refreshHandoffThreads(syncEvolution: Boolean = true) {
        viewModelScope.launch {
            if (syncEvolution) _isSyncingHandoffs.value = true
            try {
                runCatching {
                    apiService.getHandoffThreads(syncEvolution = syncEvolution, limit = 30)
                }.onSuccess { response ->
                    _handoffThreads.value = response.threads
                    _totalUnreadHandoffs.value = response.total_unread

                    var newestAlert: IncomingHandoffAlert? = null
                    val activeSid = _currentSessionId.value
                    val isInsideConversation = !_isViewingWhatsAppContactHub.value

                    for (thread in response.threads) {
                        val displayName = resolveContactDisplayName(thread)
                        val cleanTitle = formatHandoffSessionTitle(
                            roleLabel = thread.role_label,
                            contactName = displayName,
                            phone = thread.thread_phone
                        )
                        val sessionTs = if (thread.last_epoch_ts > 0L) thread.last_epoch_ts * 1000L else System.currentTimeMillis()
                        chatDao.insertSession(ChatSessionEntity(thread.session_id, cleanTitle, sessionTs))

                        for (msg in thread.messages) {
                            val isOutbound = msg.direction.equals("OUTBOUND", ignoreCase = true)
                            val msgTs = if (msg.epoch_ts > 0L) msg.epoch_ts * 1000L else System.currentTimeMillis()
                            val senderTitle = msg.sender_label.takeIf { it.isNotBlank() && !isPhoneDigitsOnly(it) } ?: displayName
                            val displayText = if (isOutbound) {
                                msg.message_text
                            } else {
                                "💬 **$senderTitle:** ${msg.message_text}"
                            }
                            chatDao.insertMessageIfAbsent(
                                ChatMessageEntity(
                                    id = "wa_msg_${msg.message_id}",
                                    sessionId = thread.session_id,
                                    text = displayText,
                                    isFromUser = isOutbound,
                                    timestamp = msgTs
                                )
                            )
                            if (!isOutbound && msg.is_read == 0) {
                                val isNewForAlert = notifiedInboundMessageIds.add(msg.message_id)
                                if (isNewForAlert && (!isInsideConversation || activeSid != thread.session_id)) {
                                    newestAlert = IncomingHandoffAlert(
                                        sessionId = thread.session_id,
                                        phone = thread.thread_phone,
                                        contactName = displayName,
                                        roleLabel = thread.role_label?.takeIf { it.isNotBlank() } ?: "WhatsApp",
                                        previewText = msg.message_text,
                                        unreadCount = thread.unread_count.coerceAtLeast(1)
                                    )
                                }
                            }
                        }

                        if (isInsideConversation && activeSid == thread.session_id && thread.unread_count > 0) {
                            markThreadRead(thread.thread_phone)
                        }
                    }

                    if (newestAlert != null) {
                        _incomingHandoffAlert.value = newestAlert
                    }
                }
            } finally {
                if (syncEvolution) _isSyncingHandoffs.value = false
            }
        }
    }

    private fun isPhoneDigitsOnly(value: String?): Boolean {
        val clean = value?.trim().orEmpty()
        if (clean.isEmpty()) return true
        val digits = clean.filter { it.isDigit() }
        return digits.length >= 8 && clean.all { it.isDigit() || it in "+()- .@swhanetlid:" }
    }

    fun formatPhoneDisplay(rawPhone: String): String {
        val norm = normalizeWhatsAppPhone(rawPhone)
        return when {
            norm.startsWith("55") && norm.length == 13 -> "+55 (${norm.substring(2, 4)}) ${norm.substring(4, 9)}-${norm.substring(9)}"
            norm.startsWith("55") && norm.length == 12 -> "+55 (${norm.substring(2, 4)}) ${norm.substring(4, 8)}-${norm.substring(8)}"
            norm.length >= 10 -> "+$norm"
            else -> rawPhone
        }
    }

    fun resolveContactDisplayName(thread: HandoffThreadDto): String {
        val role = thread.role_label?.trim().orEmpty()
        val candidate = thread.contact_name?.trim().orEmpty()
        if (candidate.isNotBlank() && !isPhoneDigitsOnly(candidate) && !candidate.equals(role, ignoreCase = true)) {
            return candidate
        }
        val inboundPush = thread.messages.lastOrNull {
            it.direction.equals("INBOUND", ignoreCase = true) &&
                it.sender_label.isNotBlank() &&
                !isPhoneDigitsOnly(it.sender_label) &&
                !it.sender_label.equals(role, ignoreCase = true)
        }?.sender_label?.trim()
        if (!inboundPush.isNullOrBlank()) return inboundPush
        if (candidate.isNotBlank() && !isPhoneDigitsOnly(candidate)) return candidate
        if (role.isNotBlank() && !role.equals("WhatsApp", ignoreCase = true)) return role
        return thread.formatted_phone?.takeIf { it.isNotBlank() } ?: formatPhoneDisplay(thread.thread_phone)
    }

    private fun formatHandoffSessionTitle(roleLabel: String?, contactName: String?, phone: String): String {
        val role = roleLabel?.takeIf { it.isNotBlank() } ?: "WhatsApp"
        val name = contactName?.takeIf { it.isNotBlank() } ?: formatPhoneDisplay(phone)
        return "📲 $name • $role"
    }

    fun openWhatsAppContactsHub() {
        _isWhatsAppReturnsMode.value = true
        _isViewingWhatsAppContactHub.value = true
        _incomingHandoffAlert.value = null
        refreshHandoffThreads(syncEvolution = true)
    }

    fun switchToAuraMode(sessionId: String = "default", title: String = "AURA") {
        _isWhatsAppReturnsMode.value = false
        _isViewingWhatsAppContactHub.value = false
        loadSession(sessionId, title)
    }

    fun openHandoffThread(sessionId: String, phone: String? = null) {
        _incomingHandoffAlert.value = null
        _isWhatsAppReturnsMode.value = true
        _isViewingWhatsAppContactHub.value = false
        val targetPhone = phone?.takeIf { it.isNotBlank() } ?: sessionId.removePrefix("wa_handoff_")
        val thread = _handoffThreads.value.firstOrNull {
            it.session_id == sessionId || it.thread_phone == targetPhone
        }
        val resolvedName = thread?.let { resolveContactDisplayName(it) }
        val title = formatHandoffSessionTitle(
            roleLabel = thread?.role_label,
            contactName = resolvedName,
            phone = targetPhone
        )
        loadSession(sessionId, title)
        markThreadRead(targetPhone)
    }

    fun dismissIncomingHandoffAlert() {
        _incomingHandoffAlert.value = null
    }

    fun markThreadRead(phone: String) {
        val cleanPhone = phone.removePrefix("wa_handoff_")
        if (cleanPhone.isBlank()) return
        viewModelScope.launch {
            runCatching { apiService.markHandoffThreadRead(cleanPhone) }
            val updated = _handoffThreads.value.map { t ->
                if (t.thread_phone == cleanPhone || t.session_id == "wa_handoff_$cleanPhone") {
                    t.copy(unread_count = 0)
                } else t
            }
            _handoffThreads.value = updated
            _totalUnreadHandoffs.value = updated.sumOf { it.unread_count }
        }
    }

    fun loadSession(sessionId: String, title: String) {
        val isSwitchingSession = _currentSessionId.value != sessionId
        _currentSessionId.value = sessionId
        _currentSessionTitle.value = title
        if (!sessionId.startsWith("wa_handoff_")) {
            _isWhatsAppReturnsMode.value = false
            _isViewingWhatsAppContactHub.value = false
        }
        if (isSwitchingSession) {
            // Limpa imediatamente a sessao anterior para evitar sobreposicao visual durante a leitura assincrona do Room
            _messages.value = emptyList()
        }

        viewModelScope.launch {
            chatDao.insertSession(ChatSessionEntity(sessionId, title))
        }

        messageCollectJob?.cancel()
        messageCollectJob = viewModelScope.launch {
            chatDao.getMessagesForSession(sessionId).collect { entities ->
                val roomList = entities.map {
                    val steps = it.reasoningJson?.let { raw ->
                        runCatching {
                            Json.parseToJsonElement(raw).jsonArray.map { elem -> elem.jsonPrimitive.content }
                        }.getOrNull()
                    } ?: emptyList()
                    ChatMessage(it.id, it.text, it.isFromUser, false, it.envelopeJson, steps)
                }
                val activeStreaming = if (!isSwitchingSession) {
                    _messages.value.firstOrNull { it.isStreaming }
                } else null
                _messages.value = if (activeStreaming != null && roomList.none { it.id == activeStreaming.id }) {
                    roomList + activeStreaming
                } else {
                    roomList
                }
            }
        }
    }

    fun createNewChat(title: String = "Novo Chat"): String {
        val newSessionId = "chat_" + System.currentTimeMillis()
        loadSession(newSessionId, title)
        return newSessionId
    }

    fun clearCurrentChat() {
        val activeSessionId = _currentSessionId.value
        viewModelScope.launch {
            chatDao.clearSessionMessages(activeSessionId)
            _messages.value = emptyList()
        }
    }

    fun deleteSession(sessionId: String) {
        viewModelScope.launch {
            chatDao.deleteSession(sessionId)
            chatDao.clearSessionMessages(sessionId)
            if (_currentSessionId.value == sessionId) {
                loadSession("default", "AURA")
            }
        }
    }

    fun sendScannedDocument(telemetry: ScannedDocumentTelemetry) {
        telemetry.previewImagePath?.let { path ->
            val f = File(path)
            if (f.exists()) {
                setLastScannedDocument(Uri.fromFile(f), telemetry.title)
            }
        }

        if (_currentSessionId.value.startsWith("wa_handoff_")) {
            sendScannedDocumentToActiveHandoff(telemetry)
            return
        }

        val cleanText = "Auditar ${telemetry.title}"
        val cardJson = buildJsonObject {
            put("type", "user_vision_card")
            put("title", telemetry.title)
            put("docType", telemetry.docType.label)
            put("sourceFormat", telemetry.sourceFormat)
            telemetry.accessKey?.let { put("accessKey", it) }
            put("accessKeyVerified", telemetry.accessKeyVerified)
            telemetry.nfeNumber?.let { put("nfeNumber", it) }
            put("highlights", telemetry.compactHighlights)
            telemetry.previewImagePath?.let { put("previewPath", it) }
        }.toString()

        sendMessage(
            query = telemetry.promptForAura,
            speakResponse = false,
            voiceMode = false,
            userDisplayText = cleanText,
            userEnvelopeJson = cardJson
        )
    }

    private fun sendScannedDocumentToActiveHandoff(telemetry: ScannedDocumentTelemetry) {
        val activeSessionId = _currentSessionId.value
        val targetPhone = activeSessionId.removePrefix("wa_handoff_")
        if (targetPhone.isBlank()) return

        val thread = _handoffThreads.value.firstOrNull {
            it.session_id == activeSessionId || it.thread_phone == targetPhone
        }
        val contactName = thread?.contact_name?.takeIf { it.isNotBlank() } ?: targetPhone
        val roleLabel = thread?.role_label?.takeIf { it.isNotBlank() }

        viewModelScope.launch {
            val snapshotPath = createPerHandoffSnapshot(targetPhone, telemetry.previewImagePath)
            val attachmentB64 = snapshotPath?.let { readPathAsBase64(it) } ?: readCachedAttachmentBase64()
            val messageBody = buildString {
                append("📄 *${telemetry.title}*\n")
                if (telemetry.compactHighlights.isNotBlank()) {
                    append("${telemetry.compactHighlights}\n")
                }
                if (telemetry.executiveSummary.isNotBlank()) {
                    append("\n${telemetry.executiveSummary.take(650)}")
                }
            }.trim()

            val cardJson = buildJsonObject {
                put("type", "user_vision_card")
                put("title", telemetry.title)
                put("docType", telemetry.docType.label)
                put("sourceFormat", telemetry.sourceFormat)
                telemetry.accessKey?.let { put("accessKey", it) }
                put("accessKeyVerified", telemetry.accessKeyVerified)
                telemetry.nfeNumber?.let { put("nfeNumber", it) }
                put("highlights", telemetry.compactHighlights)
                (snapshotPath ?: telemetry.previewImagePath)?.let { put("previewPath", it) }
            }.toString()

            _auraStatusMessage.value = "Enviando documento recortado para $contactName no WhatsApp..."
            runCatching {
                apiService.triggerHandoff(
                    HandoffRequest(
                        action_id = "wa_doc_${System.currentTimeMillis()}",
                        phone = targetPhone,
                        contact_name = contactName,
                        role_label = roleLabel,
                        initial_message = messageBody,
                        session_handoff_context = "Envio direto dos Olhos da AURA na sessao $activeSessionId",
                        attachment_base64 = attachmentB64,
                        attachment_mimetype = if (attachmentB64 != null) "image/jpeg" else null,
                        attachment_filename = if (attachmentB64 != null) "documento_recortado_aura.jpg" else null,
                        attachment_caption = if (attachmentB64 != null) "📎 *${telemetry.title}* - Olhos da AURA" else null
                    )
                )
            }.onSuccess { res ->
                val msgId = res.message_id?.let { "wa_msg_$it" } ?: "wa_local_${System.currentTimeMillis()}"
                val entity = ChatMessageEntity(
                    id = msgId,
                    sessionId = activeSessionId,
                    text = messageBody,
                    isFromUser = true,
                    envelopeJson = cardJson,
                    timestamp = System.currentTimeMillis()
                )
                chatDao.insertMessage(entity)
                _auraStatusMessage.value = null
                refreshHandoffThreads(syncEvolution = false)
            }.onFailure { err ->
                _auraStatusMessage.value = null
                val errEntity = ChatMessageEntity(
                    id = "wa_err_${System.currentTimeMillis()}",
                    sessionId = activeSessionId,
                    text = "⚠️ Falha ao enviar documento no WhatsApp (${err.localizedMessage ?: "erro de rede"}).",
                    isFromUser = false,
                    timestamp = System.currentTimeMillis()
                )
                chatDao.insertMessage(errEntity)
            }
        }
    }

    private fun sendDirectWhatsAppReply(text: String) {
        val activeSessionId = _currentSessionId.value
        val targetPhone = activeSessionId.removePrefix("wa_handoff_")
        if (targetPhone.isBlank() || text.isBlank()) return

        val thread = _handoffThreads.value.firstOrNull {
            it.session_id == activeSessionId || it.thread_phone == targetPhone
        }
        val contactName = thread?.contact_name?.takeIf { it.isNotBlank() } ?: targetPhone
        val roleLabel = thread?.role_label?.takeIf { it.isNotBlank() }

        viewModelScope.launch {
            _auraStatusMessage.value = "Enviando para $contactName no WhatsApp..."
            runCatching {
                apiService.triggerHandoff(
                    HandoffRequest(
                        action_id = "wa_reply_${System.currentTimeMillis()}",
                        phone = targetPhone,
                        contact_name = contactName,
                        role_label = roleLabel,
                        initial_message = text,
                        session_handoff_context = "Resposta direta do gestor via App Android ($activeSessionId)"
                    )
                )
            }.onSuccess { res ->
                val msgId = res.message_id?.let { "wa_msg_$it" } ?: "wa_local_${System.currentTimeMillis()}"
                val entity = ChatMessageEntity(
                    id = msgId,
                    sessionId = activeSessionId,
                    text = text,
                    isFromUser = true,
                    timestamp = System.currentTimeMillis()
                )
                chatDao.insertMessage(entity)
                _auraStatusMessage.value = null
                refreshHandoffThreads(syncEvolution = false)
            }.onFailure { err ->
                _auraStatusMessage.value = null
                val errEntity = ChatMessageEntity(
                    id = "wa_err_${System.currentTimeMillis()}",
                    sessionId = activeSessionId,
                    text = "⚠️ Falha ao enviar mensagem para $contactName (${err.localizedMessage ?: "erro de rede"}).",
                    isFromUser = false,
                    timestamp = System.currentTimeMillis()
                )
                chatDao.insertMessage(errEntity)
            }
        }
    }

    fun sendMessage(
        query: String,
        speakResponse: Boolean = false,
        voiceMode: Boolean = false,
        userDisplayText: String? = null,
        userEnvelopeJson: String? = null
    ) {
        if (query.isBlank()) return

        val activeSessionId = _currentSessionId.value
        val trimmed = query.trim()
        val effectiveQuery = if (activeSessionId.startsWith("wa_handoff_") && userEnvelopeJson == null) {
            if (trimmed.startsWith("@aura", ignoreCase = true)) {
                val stripped = trimmed.removePrefix("@aura").removePrefix("@AURA").trim()
                if (stripped.isBlank()) return
                stripped
            } else {
                sendDirectWhatsAppReply(trimmed)
                return
            }
        } else {
            query
        }

        val userMessage = ChatMessage(
            id = System.currentTimeMillis().toString(),
            text = userDisplayText ?: effectiveQuery,
            isFromUser = true,
            envelopeJson = userEnvelopeJson
        )

        viewModelScope.launch {
            chatDao.insertMessage(
                ChatMessageEntity(
                    id = userMessage.id,
                    sessionId = activeSessionId,
                    text = userMessage.text,
                    isFromUser = true,
                    envelopeJson = userMessage.envelopeJson
                )
            )
        }

        streamJob?.cancel()

        // 1. Roteamento semântico instantâneo na NPU Hexagon (< 2ms)
        val npuResult = npuEngine.classifyIntent(effectiveQuery)
        val npuStep = "⚡ Qualcomm Hexagon NPU (${"%.1f".format(npuResult.latencyMs)}ms): ${npuResult.intent.friendlyName}"

        // 2. Busca vetorial na Memória Semântica On-Device (< 2ms)
        val memoryMatches = memoryVault.searchMemories(effectiveQuery, topK = 2, minSimilarity = 0.28f)
        val memoryStep = if (memoryMatches.isNotEmpty()) {
            val best = memoryMatches.first()
            "🧠 RAG Vetorial NPU: '${best.item.title}' (${"%.1f".format(best.latencyMs)}ms, sim: ${"%.2f".format(best.similarity)})"
        } else null

        val initialSteps = listOfNotNull(npuStep, memoryStep)

        val auraMessageId = "aura_" + System.currentTimeMillis().toString()
        val streamingMessage = ChatMessage(
            id = auraMessageId,
            text = "",
            isFromUser = false,
            isStreaming = true,
            reasoningSteps = initialSteps
        )
        // Adiciona imediatamente tanto a mensagem do usuario quanto o orbe de resposta da AURA
        _messages.value = _messages.value + userMessage + streamingMessage
        _isAuraTyping.value = true
        _auraStatusMessage.value = "Processando via NPU & AURA..."

        streamJob = viewModelScope.launch {
            var currentAuraText = ""
            var currentEnvelope: String? = null
            val reasoningSteps = initialSteps.toMutableList()

            suspend fun persist(text: String) {
                if (text.isBlank() && currentEnvelope == null) return
                val reasoningJson = if (reasoningSteps.isNotEmpty()) {
                    buildJsonArray { reasoningSteps.forEach { add(JsonPrimitive(it)) } }.toString()
                } else null
                chatDao.insertMessage(
                    ChatMessageEntity(
                        id = auraMessageId,
                        sessionId = activeSessionId,
                        text = text,
                        isFromUser = false,
                        envelopeJson = currentEnvelope,
                        reasoningJson = reasoningJson
                    )
                )
            }

            var hasSpokenReply = false
            sseRepository.streamChat(effectiveQuery, sessionId = activeSessionId, voiceMode = voiceMode)
                .catch { e ->
                    val isNetworkFailure = e is ConnectException ||
                        e is SocketTimeoutException ||
                        e is java.net.NoRouteToHostException ||
                        e is java.net.UnknownHostException ||
                        e is java.io.IOException
                    if (isNetworkFailure) {
                        val cachedBriefing = offlineVault.getBriefing("postos_redes")
                        val resilientText = "📡 **Modo Resiliente Offline Ativado (Hexagon NPU SM7435)**\n\n" +
                            "O servidor local da AURA está temporariamente inacessível. O classificador neural identificou sua consulta como **${npuResult.intent.friendlyName}** e recuperou o último diagnóstico auditado em cofre local:\n\n" +
                            "${cachedBriefing.oralVoiceScript}\n\n" +
                            "💡 *Diretriz NPU:* ${npuResult.suggestedActionHint}"

                        reasoningSteps.add("Cofre Offline: Snapshot preditivo recuperado (0ms)")
                        updateAuraMessage(auraMessageId, resilientText, false, cachedBriefing.genUiCard?.toString(), reasoningSteps.toList())
                        _isAuraTyping.value = false
                        _auraStatusMessage.value = null
                        persist(resilientText)
                        if (speakResponse && !hasSpokenReply) {
                            hasSpokenReply = true
                            val spokenOffline = if (voiceMode) {
                                "Tô sem conexão com o computador agora, mas pelo último registro aqui: ${cachedBriefing.oralVoiceScript}"
                            } else {
                                "Modo offline ativado na NPU. ${cachedBriefing.oralVoiceScript}"
                            }
                            voiceManager.speak(auraMessageId, spokenOffline) {
                                relistenIfConversationActive()
                            }
                        }
                    } else {
                        val errorMessage = "Erro de conexão com a AURA: ${e.message}"
                        val finalErrorText = if (currentAuraText.isBlank()) errorMessage else currentAuraText + "\n\n" + errorMessage
                        updateAuraMessage(auraMessageId, finalErrorText, false, currentEnvelope, reasoningSteps.toList())
                        _isAuraTyping.value = false
                        _auraStatusMessage.value = null
                        persist(finalErrorText)
                        if (speakResponse && !hasSpokenReply) {
                            hasSpokenReply = true
                            voiceManager.speak(auraMessageId, finalErrorText) {
                                relistenIfConversationActive()
                            }
                        }
                    }
                }
                .onCompletion {
                    if (_isAuraTyping.value) {
                        updateAuraMessage(auraMessageId, currentAuraText, false, currentEnvelope, reasoningSteps.toList())
                        _isAuraTyping.value = false
                        _auraStatusMessage.value = null
                        persist(currentAuraText)
                        if (speakResponse && !hasSpokenReply && currentAuraText.isNotBlank()) {
                            hasSpokenReply = true
                            voiceManager.speak(auraMessageId, currentAuraText) {
                                relistenIfConversationActive()
                            }
                        }
                    }
                }
                .collect { event ->
                    when (event) {
                        is SseEvent.StatusUpdate -> {
                            val sanitized = sanitizeStatusMessage(event.statusMessage)
                            _auraStatusMessage.value = sanitized
                            if (sanitized.isNotBlank() && (reasoningSteps.isEmpty() || reasoningSteps.last() != sanitized)) {
                                reasoningSteps.add(sanitized)
                                updateAuraMessage(auraMessageId, currentAuraText, true, currentEnvelope, reasoningSteps.toList())
                            }
                        }
                        is SseEvent.TextDelta -> {
                            currentAuraText += event.text
                            updateAuraMessage(auraMessageId, currentAuraText, true, currentEnvelope, reasoningSteps.toList())
                        }
                        is SseEvent.UiComplete -> {
                            currentEnvelope = event.envelopeJson
                            updateAuraMessage(auraMessageId, currentAuraText, true, currentEnvelope, reasoningSteps.toList())
                        }
                        is SseEvent.Error -> {
                            val finalErrorText = currentAuraText + "\n\n" + event.message
                            updateAuraMessage(auraMessageId, finalErrorText, false, currentEnvelope, reasoningSteps.toList())
                            _isAuraTyping.value = false
                            _auraStatusMessage.value = null
                            persist(finalErrorText)
                        }
                        is SseEvent.Done -> {
                            updateAuraMessage(auraMessageId, currentAuraText, false, currentEnvelope, reasoningSteps.toList())
                            _isAuraTyping.value = false
                            _auraStatusMessage.value = null
                            persist(currentAuraText)
                            if (speakResponse && !hasSpokenReply && currentAuraText.isNotBlank()) {
                                hasSpokenReply = true
                                voiceManager.speak(auraMessageId, currentAuraText) {
                                    relistenIfConversationActive()
                                }
                            }
                        }
                    }
                }
        }
    }

    private fun sanitizeStatusMessage(raw: String): String {
        val lower = raw.lowercase()
        return when {
            lower.contains("previsao_tanques") || lower.contains("runout") || lower.contains("tanque") ->
                "Analisando telemetria e autonomia dos tanques..."
            lower.contains("lmc") || lower.contains("anp_tolerancia") || lower.contains("perda") ->
                "Auditando conformidade LMC e tolerâncias ANP..."
            lower.contains("turno") || lower.contains("fechamento") || lower.contains("sangria") ->
                "Conciliando fechamento de turno e sangrias..."
            lower.contains("conveniencia") || lower.contains("loja") || lower.contains("cesta") ->
                "Analisando vendas cruzadas e conveniência..."
            lower.contains("preco") || lower.contains("anp") || lower.contains("mercado") ->
                "Consultando cotações e inteligência de mercado ANP..."
            lower.contains("diagnostico") || lower.contains("diretoria") ->
                "Sintetizando diagnóstico executivo da diretoria..."
            lower.contains("executando ferramenta") ->
                "Processando dados operacionais da pista..."
            raw.isNotBlank() -> raw
            else -> "AURA está sintetizando resposta..."
        }
    }

    private fun updateAuraMessage(
        id: String,
        newText: String,
        isStreaming: Boolean,
        envelopeJson: String?,
        reasoningSteps: List<String> = emptyList()
    ) {
        val currentList = _messages.value.toMutableList()
        val index = currentList.indexOfFirst { it.id == id }
        if (index != -1) {
            val existing = currentList[index]
            currentList[index] = existing.copy(
                text = newText,
                isStreaming = isStreaming,
                envelopeJson = envelopeJson,
                reasoningSteps = if (reasoningSteps.isNotEmpty()) reasoningSteps else existing.reasoningSteps
            )
            _messages.value = currentList
        } else {
            currentList.add(
                ChatMessage(
                    id = id,
                    text = newText,
                    isFromUser = false,
                    isStreaming = isStreaming,
                    envelopeJson = envelopeJson,
                    reasoningSteps = reasoningSteps
                )
            )
            _messages.value = currentList
        }
    }

    // --- Ações de Voz Hands-Free, Push-to-Talk & TTS ---

    fun startVoiceConversation() {
        _isVoiceConversationActive.value = true
        voiceManager.stopSpeaking()
        listenForNextVoiceTurn()
    }

    private fun listenForNextVoiceTurn() {
        voiceManager.startListening { spoken ->
            sendVoiceQuery(spoken)
        }
    }

    private fun relistenIfConversationActive() {
        viewModelScope.launch {
            kotlinx.coroutines.delay(450)
            if (_isVoiceConversationActive.value && !voiceManager.isSpeaking.value && !_isAuraTyping.value) {
                listenForNextVoiceTurn()
            }
        }
    }

    fun interruptAndListen() {
        voiceManager.stopSpeaking()
        _isVoiceConversationActive.value = true
        listenForNextVoiceTurn()
    }

    fun endVoiceConversation() {
        _isVoiceConversationActive.value = false
        voiceManager.stopSpeaking()
        voiceManager.finishVoiceSession()
    }

    fun startVoiceListening() {
        startVoiceConversation()
    }

    fun sendVoiceQuery(query: String) {
        voiceManager.finishVoiceSession()
        if (query.isBlank()) return

        val routed = voiceManager.commandRouter.routeSpokenText(query)
        when (routed.action) {
            com.example.aurapostoassitance.data.audio.AuraDirectVoiceAction.STOP_AUDIO -> {
                endVoiceConversation()
            }
            com.example.aurapostoassitance.data.audio.AuraDirectVoiceAction.PLAY_BRIEFING -> {
                val cached = offlineVault.getBriefing("postos_redes")
                voiceManager.speak("voice_cmd_briefing", cached.oralVoiceScript) {
                    relistenIfConversationActive()
                }
            }
            com.example.aurapostoassitance.data.audio.AuraDirectVoiceAction.EXECUTE_OPTION_1 -> {
                sendMessage(
                    query = "Confirmo e aprovo a opção 1: Compra antecipada fracionada de combustível.",
                    speakResponse = true,
                    voiceMode = true
                )
            }
            com.example.aurapostoassitance.data.audio.AuraDirectVoiceAction.OPEN_VISION_SCANNER -> {
                _isVoiceConversationActive.value = false
                _openVisionScannerRequest.value = true
                voiceManager.speak("vision_open", "Abrindo os Olhos da Aura.")
            }
            com.example.aurapostoassitance.data.audio.AuraDirectVoiceAction.FALLBACK_CHAT_QUERY -> {
                sendMessage(query = query, speakResponse = true, voiceMode = true)
            }
        }
    }

    fun consumeVisionScannerRequest() {
        _openVisionScannerRequest.value = false
    }

    fun clearVoiceError() {
        voiceManager.clearVoiceError()
    }

    fun stopVoiceListening() {
        voiceManager.stopListening()
    }

    fun cancelVoiceListening() {
        endVoiceConversation()
    }

    fun toggleSpeech(messageId: String, text: String) {
        voiceManager.speak(messageId, text)
    }

    fun stopSpeech() {
        voiceManager.stopSpeaking()
    }

    /**
     * Autentica com biometria no Qualcomm TEE antes de assinar e executar a ação GenUI.
     */
    fun handleSignedGenUiAction(activity: FragmentActivity, action: GenUiAction) {
        val payload = "ACTION:${action.actionId}|LABEL:${action.label}|TYPE:${action.type}|TS:${System.currentTimeMillis()}"
        hardwareAuthManager.authenticateAndSignOrder(
            activity = activity,
            orderTitle = "Alçada Executiva • ${action.label}",
            orderSubtitle = "Assinatura Criptográfica Qualcomm TEE",
            orderDescription = "Confirme com a biometria para autorizar e assinar no silício do Snapdragon 7s Gen 2.",
            payloadToSign = payload,
            onSuccess = { signature, isHardware ->
                handleGenUiActionInternal(action, signature, isHardware)
            },
            onError = { errorMsg ->
                _auraStatusMessage.value = errorMsg
            }
        )
    }

    fun handleGenUiAction(action: GenUiAction) {
        handleGenUiActionInternal(action, null, false)
    }

    private fun handleGenUiActionInternal(
        action: GenUiAction,
        signature: String?,
        isHardwareBacked: Boolean
    ) {
        viewModelScope.launch {
            val activeSessionId = _currentSessionId.value
            val isHandoff = action.type.equals("handoff", ignoreCase = true) || action.actionId.startsWith("handoff_")
            val secBadge = if (isHardwareBacked) " [🔐 TEE SM7435]" else if (signature != null) " [🔑 Assinado]" else ""
            
            if (isHandoff) {
                val targetPhone = normalizeWhatsAppPhone(action.targetPhone.orEmpty())
                if (targetPhone.length < 10) {
                    _auraStatusMessage.value = "Informe um WhatsApp válido com DDD antes de enviar."
                    return@launch
                }
                val targetName = action.targetContactName?.takeIf { it.isNotBlank() }
                    ?: action.targetRole?.takeIf { it.isNotBlank() }
                    ?: "Responsável"
                val roleLabel = action.targetRole?.takeIf { it.isNotBlank() }
                val contextBody = action.contextSummary?.takeIf { it.isNotBlank() }
                val initialMsg = contextBody ?: "AURA: ${action.label}"
                val docTitle = _lastScannedDocumentTitle.value ?: "Nota Fiscal / DANFE"
                val snapshotPath = if (action.includeAttachment && _hasScannedDocument.value) {
                    createPerHandoffSnapshot(targetPhone)
                } else {
                    null
                }
                val attachmentB64 = snapshotPath?.let { readPathAsBase64(it) }
                    ?: if (action.includeAttachment && _hasScannedDocument.value) readCachedAttachmentBase64() else null

                _auraStatusMessage.value = if (attachmentB64 != null) {
                    "Enviando relatório + cópia da nota via WhatsApp..."
                } else {
                    "Enviando relatório via WhatsApp..."
                }
                try {
                    val handoffRes = apiService.triggerHandoff(
                        HandoffRequest(
                            action_id = action.actionId,
                            phone = targetPhone,
                            contact_name = targetName,
                            role_label = roleLabel,
                            initial_message = initialMsg,
                            session_handoff_context = buildString {
                                append("Gatilho App Android: ${action.label} (ID: ${action.actionId})")
                                append(" | Destinatário: $targetName ($targetPhone)")
                                if (attachmentB64 != null) append(" | Anexo: $docTitle")
                                if (contextBody != null) {
                                    append(" | Resumo: ${contextBody.replace("\n", " ").take(450)}")
                                }
                                if (signature != null) {
                                    append(" | TEE Signature: $signature | Hardware: $isHardwareBacked")
                                }
                            },
                            attachment_base64 = attachmentB64,
                            attachment_mimetype = if (attachmentB64 != null) "image/jpeg" else null,
                            attachment_filename = if (attachmentB64 != null) "copia_nota_fiscal_aura.jpg" else null,
                            attachment_caption = if (attachmentB64 != null) "📎 *Cópia do documento ($docTitle)* - Auditoria AURA" else null
                        )
                    )
                    val receipt = handoffRes.command_key ?: handoffRes.journal_id ?: "CMD-HANDOFF-OK"
                    val mediaNote = when {
                        handoffRes.media_sent == true -> "\n• *Anexo:* Cópia da nota enviada em imagem"
                        attachmentB64 != null -> "\n• *Anexo:* Cópia da nota enfileirada"
                        else -> ""
                    }
                    val dedicatedSessionId = handoffRes.session_id ?: "wa_handoff_$targetPhone"
                    val dedicatedTitle = formatHandoffSessionTitle(roleLabel, targetName, targetPhone)
                    val threadMsgId = handoffRes.message_id?.let { "wa_msg_$it" } ?: "wa_local_${System.currentTimeMillis()}"
                    val dedicatedEnvelope = snapshotPath?.let { path ->
                        buildJsonObject {
                            put("type", "user_vision_card")
                            put("title", docTitle)
                            put("docType", "Anexo Enviado no WhatsApp")
                            put("sourceFormat", "Imagem Recortada AURA")
                            put("highlights", "Enviado para $targetName ($targetPhone)")
                            put("previewPath", path)
                        }.toString()
                    }
                    chatDao.insertSession(ChatSessionEntity(dedicatedSessionId, dedicatedTitle, System.currentTimeMillis()))
                    chatDao.insertMessage(
                        ChatMessageEntity(
                            id = threadMsgId,
                            sessionId = dedicatedSessionId,
                            text = initialMsg,
                            isFromUser = true,
                            envelopeJson = dedicatedEnvelope,
                            timestamp = System.currentTimeMillis()
                        )
                    )

                    val feedbackText = "💬 **Relatório Enviado no WhatsApp$secBadge**\n\n" +
                        "• *Destinatário:* **$targetName** (`$targetPhone`)\n" +
                        "• *Protocolo Command Journal:* `${receipt}`$mediaNote\n" +
                        "• *Canal de Retorno:* Aba **Retornos WhatsApp** no Histórico\n" +
                        "• *Status:* ${handoffRes.confirmation_text ?: "Ordem contextualizada enviada com sucesso."}"

                    val feedbackMsg = ChatMessage(
                        id = System.currentTimeMillis().toString(),
                        text = feedbackText,
                        isFromUser = false
                    )
                    chatDao.insertMessage(
                        ChatMessageEntity(
                            id = feedbackMsg.id,
                            sessionId = activeSessionId,
                            text = feedbackMsg.text,
                            isFromUser = false,
                            timestamp = System.currentTimeMillis()
                        )
                    )
                    _messages.value = _messages.value + feedbackMsg
                    _auraStatusMessage.value = null
                    refreshHandoffThreads(syncEvolution = false)

                    // Indexa no Cofre Semântico RAG Local
                    memoryVault.indexMemory(
                        category = "HANDOFF_WHATSAPP",
                        title = "WhatsApp ($targetName): ${action.label}",
                        content = "Handoff enviado para $targetName ($targetPhone) — ${action.label} (Recibo: $receipt)",
                        segment = "postos_redes"
                    )

                    if (signature != null) {
                        voiceManager.speak("handoff_conf", "Ordem assinada no silício e enviada para $targetName.")
                    }
                } catch (e: retrofit2.HttpException) {
                    if (e.code() == 404) {
                        // Servidor :8000 ainda sem /api/v1/partner/handoff: registra no quick-action ativo e abre WhatsApp direto
                        val receipt = runCatching {
                            val fallbackRes = apiService.executeStationQuickAction(
                                stationId = "posto_01",
                                request = QuickActionRequest(
                                    action_type = "WHATSAPP_HANDOFF",
                                    option_key = "1",
                                    voucher_id = action.actionId,
                                    parameters = buildMap {
                                        put("target_phone", targetPhone)
                                        put("contact_name", targetName)
                                        put("label", action.label)
                                        if (contextBody != null) put("context_summary", contextBody.take(400))
                                        if (signature != null) put("tee_signature", signature)
                                    }
                                )
                            )
                            fallbackRes.journal_id ?: fallbackRes.voucher_id
                        }.getOrNull() ?: "WA-LOCAL-${System.currentTimeMillis() % 100000}"

                        val encodedMsg = java.net.URLEncoder.encode(initialMsg, "UTF-8").replace("+", "%20")
                        _pendingWhatsAppUrl.value = "https://wa.me/$targetPhone?text=$encodedMsg"
                        _auraStatusMessage.value = null

                        val feedbackText = "💬 **Resumo pronto no WhatsApp para $targetName$secBadge**\n\n" +
                            "• *WhatsApp Destino:* `$targetPhone`\n" +
                            "• *Registro Command Journal:* `$receipt`\n" +
                            "• *Modo Direto:* Como o serviço local `:8000` ainda não foi reiniciado com a rota `/partner/handoff`, abrimos o WhatsApp no aparelho com a mensagem preenchida para envio imediato."
                        val feedbackMsg = ChatMessage(
                            id = System.currentTimeMillis().toString(),
                            text = feedbackText,
                            isFromUser = false
                        )
                        chatDao.insertMessage(
                            ChatMessageEntity(
                                id = feedbackMsg.id,
                                sessionId = activeSessionId,
                                text = feedbackMsg.text,
                                isFromUser = false,
                                timestamp = System.currentTimeMillis()
                            )
                        )
                        _messages.value = _messages.value + feedbackMsg
                    } else {
                        _auraStatusMessage.value = null
                        val errText = "⚠️ **Falha ao enviar para o WhatsApp**\n\nNão foi possível registrar '${action.label}' (HTTP ${e.code()})."
                        _messages.value = _messages.value + ChatMessage(System.currentTimeMillis().toString(), errText, isFromUser = false)
                    }
                } catch (e: Exception) {
                    _auraStatusMessage.value = null
                    val errText = "⚠️ **Falha ao enviar para o WhatsApp**\n\nNão foi possível registrar '${action.label}' no Command Journal (${e.localizedMessage ?: "verifique a conexão com a AURA"})."
                    val errMsg = ChatMessage(
                        id = System.currentTimeMillis().toString(),
                        text = errText,
                        isFromUser = false
                    )
                    _messages.value = _messages.value + errMsg
                }
            } else {
                val resolvedActionType = when {
                    action.actionId.contains("fiscal", ignoreCase = true) ||
                        action.label.contains("fiscal", ignoreCase = true) ||
                        action.label.contains("SEFAZ", ignoreCase = true) -> "AUDITORIA_FISCAL_SEFAZ"
                    action.actionId.contains("combustivel", ignoreCase = true) ||
                        action.actionId.contains("pedido", ignoreCase = true) -> "PROGRAMAR_PEDIDO_COMBUSTIVEL"
                    else -> action.actionId.uppercase().take(48)
                }

                _auraStatusMessage.value = "Gravando no Command Journal..."
                try {
                    val actionRes = apiService.executeStationQuickAction(
                        stationId = "posto_01",
                        request = QuickActionRequest(
                            action_type = resolvedActionType,
                            option_key = "1",
                            voucher_id = action.actionId,
                            parameters = buildMap {
                                put("label", action.label)
                                action.contextSummary?.takeIf { it.isNotBlank() }?.let {
                                    put("context_summary", it.take(450))
                                }
                                if (signature != null) {
                                    put("tee_signature", signature)
                                    put("hardware_backed", isHardwareBacked.toString())
                                    put("security_level", hardwareAuthManager.getHardwareSecurityLevel())
                                }
                            }
                        )
                    )
                    val receipt = actionRes.journal_id ?: actionRes.voucher_id ?: "CMD-2026-OK"
                    val feedbackText = "⚡ **Ação Registrada com Sucesso$secBadge**\n\n" +
                        "${actionRes.confirmation_text ?: "Comando '${action.label}' auditado e confirmado."}\n\n" +
                        "• *Tipo:* `$resolvedActionType`\n" +
                        "• *Status:* `${actionRes.status ?: "COMPLETED"}`\n" +
                        "• *Recibo do Command Journal:* `${receipt}`"

                    val feedbackMsg = ChatMessage(
                        id = System.currentTimeMillis().toString(),
                        text = feedbackText,
                        isFromUser = false
                    )
                    chatDao.insertMessage(
                        ChatMessageEntity(
                            id = feedbackMsg.id,
                            sessionId = activeSessionId,
                            text = feedbackMsg.text,
                            isFromUser = false,
                            timestamp = System.currentTimeMillis()
                        )
                    )
                    _messages.value = _messages.value + feedbackMsg
                    _auraStatusMessage.value = null

                    // Indexa no Cofre Semântico RAG Local
                    memoryVault.indexMemory(
                        category = "DECISAO_EXECUTIVA",
                        title = action.label,
                        content = "Comando executivo '${action.label}' ($resolvedActionType) registrado no Command Journal (Recibo: $receipt, TEE: $isHardwareBacked)",
                        segment = "postos_redes"
                    )

                    if (signature != null) {
                        voiceManager.speak("action_conf", "Ordem executiva assinada no silício.")
                    }
                } catch (e: Exception) {
                    _auraStatusMessage.value = null
                    val errText = "⚠️ **Falha ao gravar ação no Command Journal**\n\nNão foi possível registrar '${action.label}' (${e.localizedMessage ?: "verifique a conexão com a AURA"})."
                    val errMsg = ChatMessage(
                        id = System.currentTimeMillis().toString(),
                        text = errText,
                        isFromUser = false
                    )
                    _messages.value = _messages.value + errMsg
                }
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        voiceManager.release()
    }
}
