package com.example.aurapostoassitance.data.remote

sealed class SseEvent {
    data class StatusUpdate(val statusMessage: String) : SseEvent()
    data class ToolResult(val summary: String) : SseEvent()
    data class CacheHit(val label: String = "Cache Semântico Local (0 tokens)") : SseEvent()
    data class TextDelta(val text: String) : SseEvent()

    /** Reserva imediata de slot GenUI (Zero-CLS) antes da chegada do envelope completo. */
    data class UiSkeleton(
        val toolCallId: String,
        val componentName: String,
        val title: String? = null
    ) : SseEvent()

    /** Hidratação progressiva de campos parciais do card GenUI sem mutar dimensões externas. */
    data class UiDelta(
        val toolCallId: String,
        val partialJson: String
    ) : SseEvent()

    /** Envelope GenUI canonico (JSON) emitido pelo backend para hidratar cards nativos. */
    data class UiComplete(val envelopeJson: String) : SseEvent()

    /** Telemetria auditável (LGPD, TTFT, latência total, origem determinística). */
    data class Telemetry(
        val ttftMs: Long? = null,
        val totalMs: Long? = null,
        val piiRedactedCount: Int = 0,
        val sourceLabel: String? = null,
        val cacheHit: Boolean = false
    ) : SseEvent()

    /** Sinal emitido pelo backend em retentativas/fallbacks para limpar buffer parcial antes de retomar. */
    object StreamReset : SseEvent()

    data class Error(val message: String) : SseEvent()
    object Done : SseEvent()
}
