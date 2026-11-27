package com.example.aurapostoassitance

import com.example.aurapostoassitance.data.remote.SseEvent
import com.example.aurapostoassitance.data.remote.SseStreamBuffer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SseStreamResetTest {

    @Test
    fun `stream_reset clears partial buffer envelope and skeleton before accumulating retried deltas`() {
        val buffer = SseStreamBuffer()

        buffer.consume(SseEvent.TextDelta("Texto parcial corrompido "))
        buffer.consume(SseEvent.UiSkeleton("call_1", "WhatIfSimulatorUI", "Carregando simulação..."))
        buffer.consume(SseEvent.UiComplete("""{"component":"WhatIfSimulatorUI"}"""))
        buffer.consume(SseEvent.TextDelta("antes do retry"))

        assertFalse(buffer.didStreamReset)
        assertEquals("Texto parcial corrompido antes do retry", buffer.text)

        buffer.consume(SseEvent.StreamReset)

        assertTrue(buffer.didStreamReset)
        assertEquals(1, buffer.resetCount)
        assertEquals("", buffer.text)
        assertNull(buffer.envelopeJson)
        assertNull(buffer.pendingSkeleton)

        buffer.consume(SseEvent.TextDelta("Resposta limpa "))
        buffer.consume(SseEvent.TextDelta("após stream_reset."))
        buffer.consume(SseEvent.Telemetry(packId = "retail_supermarket"))
        buffer.consume(SseEvent.Done)

        assertEquals("Resposta limpa após stream_reset.", buffer.text)
        assertEquals("retail_supermarket", buffer.detectedPackId)
    }

    @Test
    fun `proactive_alert never pollutes partial text buffer`() {
        val buffer = SseStreamBuffer()
        buffer.consume(SseEvent.TextDelta("Margem atual em 14,2%."))
        buffer.consume(
            SseEvent.ProactiveAlert(
                title = "Queda de Margem",
                message = "Alerta proativo detectado",
                packId = "pharmacy_health"
            )
        )
        assertEquals("Margem atual em 14,2%.", buffer.text)
        assertEquals("pharmacy_health", buffer.detectedPackId)
    }
}
