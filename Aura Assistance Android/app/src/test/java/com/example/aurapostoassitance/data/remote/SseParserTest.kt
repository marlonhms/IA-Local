package com.example.aurapostoassitance.data.remote

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SseParserTest {

    @Test
    fun `parses stream_reset event cleanly`() {
        val ev = SseChunkParser.parse("stream_reset", """{"chunk_type":"stream_reset","text":"fallback"}""")
        assertTrue(ev is SseEvent.StreamReset)
    }

    @Test
    fun `parses ui_skeleton and ui_delta for Zero-CLS slot reservation`() {
        val skel = SseChunkParser.parse(
            "ui_skeleton",
            """{"chunk_type":"ui_skeleton","data":{"tool_call_id":"call_1","component_name":"WhatIfSimulatorUI","title":"Simulando margem..."}}"""
        )
        assertTrue(skel is SseEvent.UiSkeleton)
        val s = skel as SseEvent.UiSkeleton
        assertEquals("call_1", s.toolCallId)
        assertEquals("WhatIfSimulatorUI", s.componentName)
        assertEquals("Simulando margem...", s.title)

        val delta = SseChunkParser.parse(
            "ui_delta",
            """{"chunk_type":"ui_delta","data":{"tool_call_id":"call_1","partial":true}}"""
        )
        assertTrue(delta is SseEvent.UiDelta)
    }

    @Test
    fun `parses telemetry with LGPD pii_redacted_count and latency`() {
        val ev = SseChunkParser.parse(
            "telemetry",
            """{"chunk_type":"telemetry","data":{"ttft_ms":145,"total_ms":680,"pii_redacted_count":3,"source":"SQL Read-Only","cache_hit":false}}"""
        )
        assertTrue(ev is SseEvent.Telemetry)
        val t = ev as SseEvent.Telemetry
        assertEquals(145L, t.ttftMs)
        assertEquals(680L, t.totalMs)
        assertEquals(3, t.piiRedactedCount)
        assertEquals("SQL Read-Only", t.sourceLabel)
    }

    @Test
    fun `parses cache_hit and tool_result events`() {
        val cache = SseChunkParser.parse("cache_hit", """{"chunk_type":"cache_hit","text":"Cache Semântico Local"}""")
        assertTrue(cache is SseEvent.CacheHit)

        val toolRes = SseChunkParser.parse("tool_result", """{"chunk_type":"tool_result","text":"Cálculo Python OK"}""")
        assertTrue(toolRes is SseEvent.ToolResult)
    }
}
