package com.example.aurapostoassitance.ui.genui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GenUiParserNextGenTest {

    @Test
    fun `parses WhatIfSimulatorUI without exposing technical component name`() {
        val json = """
            {
              "component_name": "render_WhatIfSimulatorUI",
              "props": {
                "product_or_scope": "Gasolina Comum",
                "base_monthly_profit": 52000.0,
                "base_margin_pct": 15.2,
                "price_delta_pct": 2.5
              }
            }
        """.trimIndent()

        val card = GenUiParser.parse(json)
        assertNotNull(card)
        assertFalse(card!!.title.contains("render_"))
        assertTrue(card.blocks.any { it is GenUiBlock.WhatIfSimulator })
        val sim = card.blocks.filterIsInstance<GenUiBlock.WhatIfSimulator>().first()
        assertEquals("Gasolina Comum", sim.productScope)
        assertEquals(52000.0, sim.baseMonthlyProfit, 0.01)
    }

    @Test
    fun `parses RealizedRoiScorecardUI with audited vouchers`() {
        val json = """
            {
              "component_name": "RealizedRoiScorecardUI",
              "props": {
                "total_roi_formatted": "R$ 18.450,00",
                "roi_multiple": "12.4x",
                "leaks_stopped": "R$ 6.200",
                "margin_gain": "R$ 12.250",
                "capture_rate_pct": "88%",
                "vouchers": [
                  {"timestamp": "Hoje 09:15", "title": "Ajuste Lote Diesel", "impact_value": "+R$ 2.100", "status": "success"}
                ]
              }
            }
        """.trimIndent()

        val card = GenUiParser.parse(json)
        assertNotNull(card)
        assertEquals("Scorecard de ROI Realizado", card!!.title)
        val roi = card.blocks.filterIsInstance<GenUiBlock.RealizedRoiScorecard>().firstOrNull()
        assertNotNull(roi)
        assertEquals("R$ 18.450,00", roi!!.totalRoiValue)
        assertEquals(1, roi.auditedVouchers.size)
    }

    @Test
    fun `parses McpActionConfirmationUI with TTL and before-after diff`() {
        val json = """
            {
              "component_name": "McpActionConfirmationUI",
              "props": {
                "target_system": "ERP Outbox",
                "operation": "Atualizar Pauta de Preços",
                "reversible": true,
                "ttl_seconds": 180,
                "before_summary": "Gasolina Comum: R$ 5,89",
                "after_summary": "Gasolina Comum: R$ 5,99",
                "voucher_hmac": "hmac_sha256_abc123456789"
              }
            }
        """.trimIndent()

        val card = GenUiParser.parse(json)
        assertNotNull(card)
        val mcp = card!!.blocks.filterIsInstance<GenUiBlock.McpActionConfirmation>().firstOrNull()
        assertNotNull(mcp)
        assertEquals("ERP Outbox", mcp!!.targetSystem)
        assertEquals(180, mcp.ttlSeconds)
        assertTrue(mcp.reversible)
    }
}
