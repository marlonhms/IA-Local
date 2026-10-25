package com.example.aurapostoassitance

import com.example.aurapostoassitance.ui.chat.AuraMarkupFormatter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AuraMarkupFormatterTest {

    @Test
    fun formatsSublinhadoAndItalico() {
        val input = "Decisão recomendada: [sublinhado]Emitir pedido[/sublinhado] de [italico]DIESEL S10[/italico]"
        val output = AuraMarkupFormatter.format(input)
        assertTrue(output.contains("<u>Emitir pedido</u>"))
        assertTrue(output.contains("<i>DIESEL S10</i>"))
    }

    @Test
    fun formatsUnclosedSublinhado() {
        val input = "Decisão recomendada: [sublinhado]Emitir pedido formal para evitar perdas"
        val output = AuraMarkupFormatter.format(input)
        assertTrue(output.contains("<u>Emitir pedido formal para evitar perdas</u>"))
    }

    @Test
    fun formatsColors() {
        val input = "Valor de [ciano]R$ 71,30[/ciano] e alerta [vermelho]crítico[/vermelho]"
        val output = AuraMarkupFormatter.format(input)
        assertTrue(output.contains("<font color=\"#06B6D4\"><b>R$ 71,30</b></font>"))
        assertTrue(output.contains("<font color=\"#EF4444\"><b>crítico</b></font>"))
    }

    @Test
    fun formatsTolerantClosures() {
        val input = "Status [verde]Conforme /verde"
        val output = AuraMarkupFormatter.format(input)
        assertTrue(output.contains("<font color=\"#10B981\"><b>Conforme</b></font>"))
    }

    @Test
    fun leavesCleanTextUntouched() {
        val input = "Tudo operando normalmente no posto."
        val output = AuraMarkupFormatter.format(input)
        assertEquals(input, output)
    }

    @Test
    fun formatsListMarkers() {
        val input = "Risco em outros 7 tanques.\n* Status Geral dos Estoques:\n● Item crítico"
        val output = AuraMarkupFormatter.format(input)
        assertTrue(output.contains("Risco em outros 7 tanques.\n\n* Status Geral dos Estoques:"))
        assertTrue(output.contains("\n\n* Item crítico"))
    }
}
