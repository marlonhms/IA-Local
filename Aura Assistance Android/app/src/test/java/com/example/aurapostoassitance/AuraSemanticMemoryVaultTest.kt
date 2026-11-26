package com.example.aurapostoassitance

import com.example.aurapostoassitance.data.local.memory.AuraSemanticMemoryVault
import com.example.aurapostoassitance.data.npu.AuraNpuEngine
import com.example.aurapostoassitance.data.npu.NpuCapabilityProbe
import com.example.aurapostoassitance.data.npu.NpuDelegateType
import com.example.aurapostoassitance.data.npu.NpuHardwareProfile
import com.example.aurapostoassitance.data.npu.NpuInferenceRuntime
import com.example.aurapostoassitance.data.npu.SiliconVendor
import com.example.aurapostoassitance.data.npu.ThermalGuardState
import kotlinx.coroutines.Dispatchers
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import kotlin.math.sqrt

class AuraSemanticMemoryVaultTest {

    private fun createTestEngine(): AuraNpuEngine {
        val probe = object : NpuCapabilityProbe() {
            override fun probeHardware() = NpuHardwareProfile(
                deviceCodename = "test",
                modelName = "jvm",
                socModel = "SM7435",
                socManufacturer = "QTI",
                vendor = SiliconVendor.QUALCOMM_HEXAGON,
                marketingName = "Test SoC",
                hasDedicatedNpu = true,
                recommendedDelegate = NpuDelegateType.NNAPI_NPU,
                cpuCores = 4,
                maxRecommendedThreads = 2,
                thermalState = ThermalGuardState.NOMINAL,
                thermalHeadroom = 0.1f
            )
            override fun readThermalGuard() = ThermalGuardState.NOMINAL to 0.1f
        }
        val runtime = object : NpuInferenceRuntime {
            override val embeddingDimension = 128
            override fun activeDelegate() = NpuDelegateType.FAST_PATH_VECTOR
            override fun isModelLoaded() = false
            override suspend fun warmUp() = NpuDelegateType.FAST_PATH_VECTOR
            override fun embed(normalizedText: String, tokens: List<String>, intentScores: FloatArray): FloatArray {
                val vec = FloatArray(128)
                for (w in tokens) {
                    val h = w.hashCode()
                    vec[(h and 0x7FFFFFFF) % 128] += 1.5f
                }
                var normSq = 0f
                for (v in vec) normSq += v * v
                val norm = sqrt(normSq)
                if (norm > 1e-6f) {
                    for (i in vec.indices) vec[i] /= norm
                }
                return vec
            }
            override fun release() {}
        }
        return AuraNpuEngine(probe, runtime)
    }

    @Test
    fun `binary persistence roundtrip and multi-domain pack isolation work`() {
        val tempDir = Files.createTempDirectory("aura_rag_test").toFile()
        try {
            val engine = createTestEngine()
            val vault1 = AuraSemanticMemoryVault(tempDir, engine, Dispatchers.Unconfined, saveDebounceMs = 0L)
            vault1.indexMemory(
                category = "SCAN_DOCUMENTO",
                title = "DANFE Diesel S10 Distribuidora",
                content = "Nota fiscal 45890 com 15000 litros de diesel s10",
                segment = "postos_redes"
            )
            vault1.indexMemory(
                category = "DECISAO_EXECUTIVA",
                title = "Reposicao Estoque Varejo Moda",
                content = "Pedido de camisetas e calcados para loja matriz",
                segment = "varejo"
            )
            vault1.flushToDiskNow()

            // Recarrega do arquivo binário v2 em uma nova instância
            val vault2 = AuraSemanticMemoryVault(tempDir, engine, Dispatchers.Unconfined, saveDebounceMs = 0L)
            vault2.loadFromDiskInternal()

            val postoMatches = vault2.searchMemories("diesel s10 nota fiscal", segment = "postos_redes", topK = 3, minSimilarity = 0.2f)
            assertTrue(postoMatches.isNotEmpty())
            assertEquals("DANFE Diesel S10 Distribuidora", postoMatches.first().item.title)
            assertTrue(postoMatches.none { it.item.segment == "varejo" })

            val varejoMatches = vault2.searchMemories("camisetas loja matriz", segment = "varejo", topK = 3, minSimilarity = 0.2f)
            assertTrue(varejoMatches.isNotEmpty())
            assertEquals("Reposicao Estoque Varejo Moda", varejoMatches.first().item.title)
            assertTrue(varejoMatches.none { it.item.segment == "postos_redes" })
        } finally {
            tempDir.deleteRecursively()
        }
    }
}
