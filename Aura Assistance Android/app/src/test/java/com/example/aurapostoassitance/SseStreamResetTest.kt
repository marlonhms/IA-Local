package com.example.aurapostoassitance

import com.example.aurapostoassitance.data.remote.SseEvent
import org.junit.Assert.assertEquals
import org.junit.Test

class SseStreamResetTest {

    @Test
    fun `stream_reset clears partial buffer before accumulating retried deltas`() {
        val events = listOf(
            SseEvent.TextDelta("Texto parcial corrompido "),
            SseEvent.TextDelta("antes do retry"),
            SseEvent.StreamReset,
            SseEvent.TextDelta("Resposta limpa "),
            SseEvent.TextDelta("após stream_reset."),
            SseEvent.Done
        )

        var buffer = ""
        for (event in events) {
            when (event) {
                is SseEvent.TextDelta -> buffer += event.text
                is SseEvent.StreamReset -> buffer = ""
                else -> Unit
            }
        }

        assertEquals("Resposta limpa após stream_reset.", buffer)
    }
}
