package com.example.aurapostoassitance.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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
import java.net.ConnectException
import java.net.SocketTimeoutException
import javax.inject.Inject

data class ChatMessage(
    val id: String,
    val text: String,
    val isFromUser: Boolean,
    val isStreaming: Boolean = false
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val sseRepository: SseRepository,
    private val chatDao: ChatDao
) : ViewModel() {

    private val _currentSessionId = MutableStateFlow("default")
    val currentSessionId: StateFlow<String> = _currentSessionId.asStateFlow()

    private val _currentSessionTitle = MutableStateFlow("AURA Cockpit")
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

    init {
        // Collect all chat sessions
        viewModelScope.launch {
            chatDao.getAllSessions().collect { sessionList ->
                _sessions.value = sessionList
            }
        }
        // Load default session
        loadSession("default", "AURA Cockpit")
    }

    fun loadSession(sessionId: String, title: String) {
        _currentSessionId.value = sessionId
        _currentSessionTitle.value = title

        // Ensure session exists in DB
        viewModelScope.launch {
            chatDao.insertSession(ChatSessionEntity(sessionId, title))
        }

        // Cancel previous message collector and collect for new session
        messageCollectJob?.cancel()
        messageCollectJob = viewModelScope.launch {
            chatDao.getMessagesForSession(sessionId).collect { entities ->
                val uiMessages = entities.map {
                    ChatMessage(it.id, it.text, it.isFromUser, false)
                }
                _messages.value = uiMessages
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
                loadSession("default", "AURA Cockpit")
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
                    isFromUser = userMessage.isFromUser
                )
            )
        }

        val auraMessageId = "aura_" + System.currentTimeMillis().toString()
        val auraEmptyMessage = ChatMessage(
            id = auraMessageId,
            text = "",
            isFromUser = false,
            isStreaming = true
        )
        
        _messages.value = _messages.value + auraEmptyMessage
        _isAuraTyping.value = true
        _auraStatusMessage.value = "⚡ Conectando à AURA..."

        viewModelScope.launch {
            var currentAuraText = ""

            sseRepository.streamChat(query, sessionId = activeSessionId)
                .catch { e ->
                    val errorMessage = if (e is SocketTimeoutException) {
                        "⚠️ O sinal de rede está fraco (Timeout). Chegue mais perto do Wi-Fi do posto para concluir a consulta."
                    } else if (e is ConnectException) {
                        "⚠️ Sem conexão. O servidor da AURA não foi alcançado na rede local."
                    } else {
                        "⚠️ Erro de conexão com a AURA: ${e.message}"
                    }
                    val finalErrorText = if (currentAuraText.isBlank()) errorMessage else currentAuraText + "\n\n" + errorMessage
                    updateAuraMessage(auraMessageId, finalErrorText, false)
                    _isAuraTyping.value = false
                    _auraStatusMessage.value = null
                    chatDao.insertMessage(
                        ChatMessageEntity(
                            id = auraMessageId,
                            sessionId = activeSessionId,
                            text = finalErrorText,
                            isFromUser = false
                        )
                    )
                }
                .onCompletion {
                    if (_isAuraTyping.value) {
                        updateAuraMessage(auraMessageId, currentAuraText, false)
                        _isAuraTyping.value = false
                        _auraStatusMessage.value = null
                        if (currentAuraText.isNotBlank()) {
                            chatDao.insertMessage(
                                ChatMessageEntity(
                                    id = auraMessageId,
                                    sessionId = activeSessionId,
                                    text = currentAuraText,
                                    isFromUser = false
                                )
                            )
                        }
                    }
                }
                .collect { event ->
                    when (event) {
                        is SseEvent.StatusUpdate -> {
                            _auraStatusMessage.value = event.statusMessage
                        }
                        is SseEvent.TextDelta -> {
                            currentAuraText += event.text
                            updateAuraMessage(auraMessageId, currentAuraText, true)
                        }
                        is SseEvent.Error -> {
                            val finalErrorText = currentAuraText + "\n\n⚠️ " + event.message
                            updateAuraMessage(auraMessageId, finalErrorText, false)
                            _isAuraTyping.value = false
                            _auraStatusMessage.value = null
                            chatDao.insertMessage(
                                ChatMessageEntity(
                                    id = auraMessageId,
                                    sessionId = activeSessionId,
                                    text = finalErrorText,
                                    isFromUser = false
                                )
                            )
                        }
                        is SseEvent.Done -> {
                            updateAuraMessage(auraMessageId, currentAuraText, false)
                            _isAuraTyping.value = false
                            _auraStatusMessage.value = null
                            if (currentAuraText.isNotBlank()) {
                                chatDao.insertMessage(
                                    ChatMessageEntity(
                                        id = auraMessageId,
                                        sessionId = activeSessionId,
                                        text = currentAuraText,
                                        isFromUser = false
                                    )
                                )
                            }
                        }
                    }
                }
        }
    }

    private fun updateAuraMessage(id: String, newText: String, isStreaming: Boolean) {
        val currentList = _messages.value.toMutableList()
        val index = currentList.indexOfFirst { it.id == id }
        if (index != -1) {
            currentList[index] = currentList[index].copy(
                text = newText,
                isStreaming = isStreaming
            )
            _messages.value = currentList
        }
    }
}
