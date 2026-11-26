package com.example.aurapostoassitance.ui.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AuraDomainAdapterTest {

    @Test
    fun `supports all 5 canonical Carbon Core domain packs`() {
        val packIds = AuraDomainAdapter.allProfiles.map { it.packId }.toSet()
        assertEquals(
            setOf(
                "fuel_convenience",
                "pharmacy_health",
                "retail_supermarket",
                "autocenter_parts",
                "wholesale_distribution"
            ),
            packIds
        )
    }

    @Test
    fun `normalizes legacy segment keys cleanly`() {
        assertEquals("fuel_convenience", AuraDomainAdapter.normalizePackId("postos_redes"))
        assertEquals("pharmacy_health", AuraDomainAdapter.normalizePackId("saude_clinicas"))
        assertEquals("retail_supermarket", AuraDomainAdapter.normalizePackId("varejo"))
        assertEquals("wholesale_distribution", AuraDomainAdapter.normalizePackId("logistica"))
    }

    @Test
    fun `adapts labels and compliance controls outside fuel vertical`() {
        val pharma = AuraDomainAdapter.profileFor("pharmacy_health")
        assertEquals("Estoque", pharma.resourceTabLabel)
        assertEquals("SNGPC", pharma.complianceButtonLabel)
        assertTrue(pharma.composerPlaceholder.contains("SNGPC"))
    }
}
