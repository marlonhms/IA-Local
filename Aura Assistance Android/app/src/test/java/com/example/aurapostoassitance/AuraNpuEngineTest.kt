package com.example.aurapostoassitance

import com.example.aurapostoassitance.data.npu.AuraNpuEngine
import com.example.aurapostoassitance.data.npu.LocalAuraIntent
import com.example.aurapostoassitance.data.npu.NpuCapabilityProbe
import com.example.aurapostoassitance.data.npu.NpuDelegateType
import com.example.aurapostoassitance.data.npu.NpuHardwareProfile
import com.example.aurapostoassitance.data.npu.NpuInferenceRuntime
import com.example.aurapostoassitance.data.npu.SiliconVendor
import com.example.aurapostoassitance.data.npu.ThermalGuardState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.sqrt

class AuraNpuEngineTest {

    private class FakeProbe(
        private val thermal: ThermalGuardState = ThermalGuardState.NOMINAL
    ) : NpuCapabilityProbe() {
        override fun probeHardware(): NpuHardwareProfile = NpuHardwareProfile(
            deviceCodename = "garnet",
            modelName = "2312DRA50G",
            socModel = "SM7435",
            socManufacturer = "QTI",
            vendor = SiliconVendor.QUALCOMM_HEXAGON,
            marketingName = "Qualcomm Snapdragon 7s Gen 2 (Hexagon NPU)",
            hasDedicatedNpu = true,
            recommendedDelegate = NpuDelegateType.NNAPI_NPU,
            cpuCores = 8,
            maxRecommendedThreads = 4,
            thermalState = thermal,
            thermalHeadroom = 0.25f
        )

        override fun readThermalGuard(): Pair<ThermalGuardState, Float> = thermal to 0.25f
    }

    private class FakeRuntime(
        private val delegate: NpuDelegateType = NpuDelegateType.FAST_PATH_VECTOR,
        private val loaded: Boolean = false
    ) : NpuInferenceRuntime {
        override val embeddingDimension: Int = 128
        override fun activeDelegate(): NpuDelegateType = delegate
        override fun isModelLoaded(): Boolean = loaded
        override suspend fun warmUp(): NpuDelegateType = delegate
        override fun embed(normalizedText: String, tokens: List<String>, intentScores: FloatArray): FloatArray {
            val vec = FloatArray(128)
            for (t in tokens) {
                val idx = (t.hashCode() and 0x7FFFFFFF) % 128
                vec[idx] += 1.0f
            }
            for (i in intentScores.indices) {
                if (intentScores[i] > 0f) {
                    vec[(i * 16) % 128] += intentScores[i]
                }
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

    @Test
    fun `classifyIntent routes runout and leakage accurately`() {
        val engine = AuraNpuEngine(FakeProbe(), FakeRuntime())

        val runout = engine.classifyIntent("Qual a previsão de ruptura e autonomia do tanque de Diesel S10?")
        assertEquals(LocalAuraIntent.PREDICTIVE_RUNOUT, runout.intent)
        assertTrue(runout.confidence >= 0.65f)

        val leakage = engine.classifyIntent("Audite fuga invisivel de caixa e descontos sem alcada")
        assertEquals(LocalAuraIntent.FINANCIAL_LEAKAGE, leakage.intent)
        assertTrue(leakage.confidence >= 0.65f)
    }

    @Test
    fun `telemetry reflects real delegate honestly`() = runBlocking {
        val fastPathEngine = AuraNpuEngine(FakeProbe(), FakeRuntime(NpuDelegateType.FAST_PATH_VECTOR, false))
        fastPathEngine.warmUp()
        assertFalse(fastPathEngine.hardwareStatus.value.isHardwareAccelerated)
        assertFalse(fastPathEngine.hardwareStatus.value.modelLoaded)

        val nnapiEngine = AuraNpuEngine(FakeProbe(), FakeRuntime(NpuDelegateType.NNAPI_NPU, true))
        nnapiEngine.warmUp()
        assertTrue(nnapiEngine.hardwareStatus.value.isHardwareAccelerated)
        assertTrue(nnapiEngine.hardwareStatus.value.modelLoaded)
        assertEquals(NpuDelegateType.NNAPI_NPU.label, nnapiEngine.hardwareStatus.value.delegateType)
    }

    @Test
    fun `concurrent classifyIntent increments inference counter atomically`() = runBlocking {
        val engine = AuraNpuEngine(FakeProbe(), FakeRuntime())
        val jobs = (1..40).map { i ->
            async(Dispatchers.Default) {
                engine.classifyIntent("auditoria turno fechamento $i")
            }
        }
        jobs.awaitAll()
        assertEquals(40, engine.hardwareStatus.value.totalInferences)
    }
}
