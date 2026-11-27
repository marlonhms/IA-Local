package com.example.aurapostoassitance.data.remote

/**
 * Acumulador determinístico e testável de eventos SSE para uma resposta em andamento.
 * Garante que `SseEvent.StreamReset` limpe imediatamente o buffer parcial (texto,
 * envelope GenUI e skeleton) antes da concatenação de novos chunks.
 */
class SseStreamBuffer {

    var text: String = ""
        private set

    var envelopeJson: String? = null
        private set

    var pendingSkeleton: String? = null
        private set

    var didStreamReset: Boolean = false
        private set

    var resetCount: Int = 0
        private set

    var detectedPackId: String? = null
        private set

    fun consume(event: SseEvent) {
        when (event) {
            is SseEvent.StreamReset -> {
                text = ""
                envelopeJson = null
                pendingSkeleton = null
                didStreamReset = true
                resetCount += 1
            }
            is SseEvent.TextDelta -> {
                text += event.text
            }
            is SseEvent.UiSkeleton -> {
                pendingSkeleton = event.title ?: "Preparando diagnóstico executivo..."
            }
            is SseEvent.UiDelta -> {
                if (pendingSkeleton == null) {
                    pendingSkeleton = "Hidratando indicadores..."
                }
            }
            is SseEvent.UiComplete -> {
                envelopeJson = event.envelopeJson
                pendingSkeleton = null
            }
            is SseEvent.Telemetry -> {
                event.packId?.takeIf { it.isNotBlank() }?.let { detectedPackId = it }
            }
            is SseEvent.ProactiveAlert -> {
                event.packId?.takeIf { it.isNotBlank() }?.let { detectedPackId = it }
            }
            is SseEvent.StatusUpdate,
            is SseEvent.ToolResult,
            is SseEvent.CacheHit,
            is SseEvent.Error,
            is SseEvent.Done -> Unit
        }
    }
}
