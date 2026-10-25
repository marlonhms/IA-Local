package com.example.aurapostoassitance

import com.example.aurapostoassitance.ui.genui.GenUiBlock
import com.example.aurapostoassitance.ui.genui.GenUiParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GenUiParserTest {

    @Test
    fun parsesTankPredictionEnvelope() {
        val json = """
            {
                "component_name": "render_TankRunOutForecastUI",
                "props": {
                    "assessment": {
                        "severity": "critical",
                        "title": "Alerta Crítico: Risco de Esgotamento de Tanques",
                        "badge_label": "Crítico / Risco de Falta"
                    },
                    "metrics": {
                        "saldo_total_litros": 52848.18,
                        "capacidade_total_litros": 416000.0,
                        "ocupacao_geral_pct": 12.7,
                        "tanques_criticos_count": 7,
                        "espaco_livre_ullage_total_litros": 363151.82
                    },
                    "tanks": [
                        {
                            "codtan": "001",
                            "combustivel": "GASOLINA COMUM",
                            "capacidade_litros": 50000.0,
                            "saldo_atual_litros": 0.0,
                            "ocupacao_pct": 0.0,
                            "autonomia_critica_horas": 0.0,
                            "alerta_critico": true,
                            "status_operacional": "ATIVO"
                        },
                        {
                            "codtan": "002",
                            "combustivel": "GASOLINA ADITIVADA",
                            "capacidade_litros": 50000.0,
                            "saldo_atual_litros": 19960.0,
                            "ocupacao_pct": 39.9,
                            "autonomia_critica_horas": 249.2,
                            "alerta_critico": false,
                            "status_operacional": "ATIVO"
                        }
                    ]
                },
                "actions": [
                    {
                        "action_id": "pedir_carreta",
                        "label": "Pedir Carreta de Combustível (15.000 L)",
                        "action_type": "mutation",
                        "variant": "primary",
                        "requires_confirmation": true
                    }
                ]
            }
        """.trimIndent()

        val card = GenUiParser.parse(json)
        assertNotNull(card)
        assertEquals("Alerta Crítico: Risco de Esgotamento de Tanques", card!!.title)
        assertEquals("critical", card.severity)
        assertEquals(1, card.actions.size)
        assertEquals("Pedir Carreta de Combustível (15.000 L)", card.actions[0].label)

        val hasTanks = card.blocks.any { it is GenUiBlock.Tanks }
        val hasKpis = card.blocks.any { it is GenUiBlock.KpiGrid }
        assertTrue(hasTanks)
        assertTrue(hasKpis)
    }

    @Test
    fun friendlyTitleRemovesTechnicalPrefix() {
        val title = GenUiParser.friendlyTitle("render_GenerativeModularCardUI", null)
        assertEquals("Diagnóstico Executivo Modular", title)
    }
}
