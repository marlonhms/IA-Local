package com.example.aurapostoassitance.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aurapostoassitance.data.audio.AuraVoiceManager
import com.example.aurapostoassitance.data.local.ChatDao
import com.example.aurapostoassitance.data.local.ChatMessageEntity
import com.example.aurapostoassitance.data.local.ChatSessionEntity
import com.example.aurapostoassitance.data.remote.SseEvent
import com.example.aurapostoassitance.data.remote.SseRepository
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
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
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

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val sseRepository: SseRepository,
    private val chatDao: ChatDao,
    private val voiceManager: AuraVoiceManager
) : ViewModel() {

    // --- Fluxos de Voz e Fala Hands-Free ---
    val isListening: StateFlow<Boolean> = voiceManager.isListening
    val spokenText: StateFlow<String> = voiceManager.spokenText
    val voiceRms: StateFlow<Float> = voiceManager.voiceRms
    val isSpeaking: StateFlow<Boolean> = voiceManager.isSpeaking
    val speakingMessageId: StateFlow<String?> = voiceManager.speakingMessageId

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

    private var messageCollectJob: Job? = null
    private var streamJob: Job? = null

    init {
        viewModelScope.launch {
            chatDao.getAllSessions().collect { sessionList ->
                _sessions.value = sessionList
            }
        }
        loadSession("default", "AURA")
    }

    fun loadSession(sessionId: String, title: String) {
        _currentSessionId.value = sessionId
        _currentSessionTitle.value = title

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
                val activeStreaming = _messages.value.firstOrNull { it.isStreaming }
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

    fun sendMessage(query: String) {
        if (query.isBlank()) return

        val activeSessionId = _currentSessionId.value

        val userMessage = ChatMessage(
            id = System.currentTimeMillis().toString(),
            text = query,
            isFromUser = true
        )

        viewModelScope.launch {
            chatDao.insertMessage(
                ChatMessageEntity(
                    id = userMessage.id,
                    sessionId = activeSessionId,
                    text = userMessage.text,
                    isFromUser = true
                )
            )
        }

        streamJob?.cancel()

        val auraMessageId = "aura_" + System.currentTimeMillis().toString()
        val streamingMessage = ChatMessage(
            id = auraMessageId,
            text = "",
            isFromUser = false,
            isStreaming = true,
            reasoningSteps = emptyList()
        )
        // Adiciona imediatamente tanto a mensagem do usuario quanto o orbe de resposta da AURA
        _messages.value = _messages.value + userMessage + streamingMessage
        _isAuraTyping.value = true
        _auraStatusMessage.value = "Conectando à AURA..."

        streamJob = viewModelScope.launch {
            var currentAuraText = ""
            var currentEnvelope: String? = null
            val reasoningSteps = mutableListOf<String>()

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

            sseRepository.streamChat(query, sessionId = activeSessionId)
                .catch { e ->
                    val errorMessage = when (e) {
                        is SocketTimeoutException -> "O sinal de rede está fraco (Timeout). Chegue mais perto do Wi-Fi do posto para concluir a consulta."
                        is ConnectException -> "Sem conexão. O servidor da AURA não foi alcançado na rede local."
                        else -> "Erro de conexão com a AURA: ${e.message}"
                    }
                    val finalErrorText = if (currentAuraText.isBlank()) errorMessage else currentAuraText + "\n\n" + errorMessage
                    updateAuraMessage(auraMessageId, finalErrorText, false, currentEnvelope, reasoningSteps.toList())
                    _isAuraTyping.value = false
                    _auraStatusMessage.value = null
                    persist(finalErrorText)
                }
                .onCompletion {
                    if (_isAuraTyping.value) {
                        updateAuraMessage(auraMessageId, currentAuraText, false, currentEnvelope, reasoningSteps.toList())
                        _isAuraTyping.value = false
                        _auraStatusMessage.value = null
                        persist(currentAuraText)
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

    // --- Ações de Voz Push-to-Talk & TTS ---

    fun startVoiceListening() {
        voiceManager.startListening { _ -> }
    }

    fun sendVoiceQuery(query: String) {
        voiceManager.finishVoiceSession()
        if (query.isNotBlank()) {
            sendMessage(query)
        }
    }

    fun stopVoiceListening() {
        voiceManager.stopListening()
    }

    fun cancelVoiceListening() {
        voiceManager.finishVoiceSession()
    }

    fun toggleSpeech(messageId: String, text: String) {
        voiceManager.speak(messageId, text)
    }

    fun stopSpeech() {
        voiceManager.stopSpeaking()
    }

    override fun onCleared() {
        super.onCleared()
        voiceManager.release()
    }
}
