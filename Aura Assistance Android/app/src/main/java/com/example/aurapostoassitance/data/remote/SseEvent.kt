package com.example.aurapostoassitance.data.remote

sealed class SseEvent {
    data class StatusUpdate(val statusMessage: String) : SseEvent()
    data class TextDelta(val text: String) : SseEvent()
    data class Error(val message: String) : SseEvent()
    object Done : SseEvent()
}
