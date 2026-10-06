package com.example.aurapostoassitance.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aurapostoassitance.data.local.ChatDao
import com.example.aurapostoassitance.data.local.ChatMessageEntity
import com.example.aurapostoassitance.data.remote.SseEvent
import com.example.aurapostoassitance.data.remote.SseRepository
import dagger.hilt.android.lifecycle.HiltViewModel
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

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    private val _isAuraTyping = MutableStateFlow(false)
    val isAuraTyping: StateFlow<Boolean> = _isAuraTyping.asStateFlow()

    private val _auraStatusMessage = MutableStateFlow<String?>(null)
    val auraStatusMessage: StateFlow<String?> = _auraStatusMessage.asStateFlow()

    init {
        viewModelScope.launch {
            chatDao.getAllMessages().collect { entities ->
                val uiMessages = entities.map {
                    ChatMessage(it.id, it.text, it.isFromUser, false)
                }
                _messages.value = uiMessages
            }
        }
    }

    fun sendMessage(query: String) {
        if (query.isBlank()) return

        val userMessage = ChatMessage(
            id = System.currentTimeMillis().toString(),
            text = query,
            isFromUser = true
        )
        
        viewModelScope.launch {
            chatDao.insertMessage(ChatMessageEntity(userMessage.id, userMessage.text, userMessage.isFromUser))
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

            sseRepository.streamChat(query)
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
                    chatDao.insertMessage(ChatMessageEntity(auraMessageId, finalErrorText, false))
                }
                .onCompletion {
                    if (_isAuraTyping.value) {
                        updateAuraMessage(auraMessageId, currentAuraText, false)
                        _isAuraTyping.value = false
                        _auraStatusMessage.value = null
                        if (currentAuraText.isNotBlank()) {
                            chatDao.insertMessage(ChatMessageEntity(auraMessageId, currentAuraText, false))
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
                            chatDao.insertMessage(ChatMessageEntity(auraMessageId, finalErrorText, false))
                        }
                        is SseEvent.Done -> {
                            updateAuraMessage(auraMessageId, currentAuraText, false)
                            _isAuraTyping.value = false
                            _auraStatusMessage.value = null
                            if (currentAuraText.isNotBlank()) {
                                chatDao.insertMessage(ChatMessageEntity(auraMessageId, currentAuraText, false))
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
