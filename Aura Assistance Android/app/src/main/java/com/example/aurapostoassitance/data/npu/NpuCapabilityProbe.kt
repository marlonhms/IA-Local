package com.example.aurapostoassitance.data.npu

import android.content.Context
import android.os.Build
import android.os.PowerManager
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

enum class SiliconVendor(val displayName: String) {
    QUALCOMM_HEXAGON("Qualcomm Hexagon NPU"),
    MEDIATEK_APU("MediaTek Dimensity APU"),
    GOOGLE_TENSOR("Google Tensor TPU"),
    SAMSUNG_EXYNOS("Samsung Exynos NPU"),
    GENERIC_MOBILE("Universal Mobile SoC")
}

enum class NpuDelegateType(val label: String, val isHardwareNpuOrGpu: Boolean) {
    NNAPI_NPU("LiteRT NNAPI/Hexagon NPU", true),
    GPU_DELEGATE("LiteRT GPU Delegate (FP16)", true),
    CPU_XNNPACK("LiteRT XNNPACK SIMD CPU", false),
    FAST_PATH_VECTOR("Fast-Path Vector Engine (CPU)", false)
}

enum class ThermalGuardState(val label: String, val allowNpuOffload: Boolean) {
    NOMINAL("Nominal", true),
    LIGHT("Aquecido (Leve)", true),
    MODERATE("Moderado (Throttling)", false),
    SEVERE("Crítico (Proteção Térmica)", false)
}

data class NpuHardwareProfile(
    val deviceCodename: String,
    val modelName: String,
    val socModel: String,
    val socManufacturer: String,
    val vendor: SiliconVendor,
    val marketingName: String,
    val hasDedicatedNpu: Boolean,
    val recommendedDelegate: NpuDelegateType,
    val cpuCores: Int,
    val maxRecommendedThreads: Int,
    val thermalState: ThermalGuardState,
    val thermalHeadroom: Float
)

/**
 * Introspecção multi-fabricante de silício (Qualcomm Hexagon, MediaTek APU, Google Tensor, Exynos)
 * combinada com governança térmica em tempo real via PowerManager (API 29+).
 */
@Singleton
open class NpuCapabilityProbe private constructor(
    private val context: Context?,
    @Suppress("UNUSED_PARAMETER") unused: Unit
) {
    @Inject
    constructor(@ApplicationContext context: Context) : this(context, Unit)

    internal constructor() : this(null, Unit)

    private val powerManager: PowerManager? by lazy {
        context?.getSystemService(Context.POWER_SERVICE) as? PowerManager
    }

    open fun probeHardware(): NpuHardwareProfile {
        val deviceCodename = Build.DEVICE.orEmpty()
        val model = Build.MODEL.orEmpty()
        val hardware = Build.HARDWARE.orEmpty()
        val manufacturer = Build.MANUFACTURER.orEmpty()
        val cpuCores = Runtime.getRuntime().availableProcessors().coerceAtLeast(1)

        val socModel = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            Build.SOC_MODEL.orEmpty()
        } else {
            hardware
        }
        val socManufacturer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            Build.SOC_MANUFACTURER.orEmpty()
        } else {
            manufacturer
        }

        val combined = "$socModel $socManufacturer $hardware $deviceCodename $model".uppercase()

        val isGarnet = deviceCodename.equals("garnet", ignoreCase = true) ||
            model.contains("2312DRA50G", ignoreCase = true)
        val isSnapdragon7s = combined.contains("SM7435")
        val isQualcomm = isGarnet || isSnapdragon7s ||
            combined.contains("QTI") || combined.contains("QUALCOMM") ||
            combined.contains("QCOM") || Regex("\\bSM\\d{4}").containsMatchIn(combined)
        val isMediaTek = combined.contains("MEDIATEK") || Regex("\\bMT6\\d{3}").containsMatchIn(combined)
        val isGoogleTensor = combined.contains("TENSOR") || Regex("\\bGS\\d{3}").containsMatchIn(combined)
        val isExynos = combined.contains("EXYNOS") || combined.contains("S5E")

        val vendor = when {
            isQualcomm -> SiliconVendor.QUALCOMM_HEXAGON
            isMediaTek -> SiliconVendor.MEDIATEK_APU
            isGoogleTensor -> SiliconVendor.GOOGLE_TENSOR
            isExynos -> SiliconVendor.SAMSUNG_EXYNOS
            else -> SiliconVendor.GENERIC_MOBILE
        }

        val hasDedicatedNpu = vendor != SiliconVendor.GENERIC_MOBILE && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q

        val marketingName = when {
            isGarnet && isSnapdragon7s -> "Qualcomm Snapdragon 7s Gen 2 (Hexagon NPU)"
            isGarnet -> "Redmi Note 13 Pro 5G (Snapdragon 7s Gen 2)"
            isSnapdragon7s -> "Snapdragon 7s Gen 2 (SM7435 • Hexagon NPU)"
            isQualcomm -> "Qualcomm Snapdragon (${socModel.ifBlank { "Hexagon NPU" }})"
            isMediaTek -> "MediaTek Dimensity (${socModel.ifBlank { "APU" }})"
            isGoogleTensor -> "Google Tensor (${socModel.ifBlank { "Edge TPU" }})"
            isExynos -> "Samsung Exynos (${socModel.ifBlank { "NPU" }})"
            else -> "${manufacturer.replaceFirstChar { it.uppercase() }} $model"
        }

        val (thermalState, thermalHeadroom) = readThermalGuard()

        val recommendedDelegate = when {
            !thermalState.allowNpuOffload -> NpuDelegateType.CPU_XNNPACK
            hasDedicatedNpu && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q -> NpuDelegateType.NNAPI_NPU
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.O -> NpuDelegateType.GPU_DELEGATE
            else -> NpuDelegateType.CPU_XNNPACK
        }

        val maxThreads = when {
            !thermalState.allowNpuOffload -> 2
            cpuCores >= 8 -> 4
            cpuCores >= 4 -> 2
            else -> 1
        }

        return NpuHardwareProfile(
            deviceCodename = deviceCodename,
            modelName = model,
            socModel = socModel.ifBlank { if (isGarnet) "SM7435" else "Universal" },
            socManufacturer = socManufacturer.ifBlank { manufacturer },
            vendor = vendor,
            marketingName = marketingName,
            hasDedicatedNpu = hasDedicatedNpu,
            recommendedDelegate = recommendedDelegate,
            cpuCores = cpuCores,
            maxRecommendedThreads = maxThreads,
            thermalState = thermalState,
            thermalHeadroom = thermalHeadroom
        )
    }

    open fun readThermalGuard(): Pair<ThermalGuardState, Float> {
        val pm = powerManager ?: return ThermalGuardState.NOMINAL to 0.0f
        return try {
            val status = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                pm.currentThermalStatus
            } else {
                0
            }
            val headroom = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                pm.getThermalHeadroom(10).takeIf { !it.isNaN() && it >= 0f } ?: 0.0f
            } else {
                0.0f
            }

            val state = when {
                status >= PowerManager.THERMAL_STATUS_SEVERE || headroom >= 0.92f -> ThermalGuardState.SEVERE
                status >= PowerManager.THERMAL_STATUS_MODERATE || headroom >= 0.78f -> ThermalGuardState.MODERATE
                status >= PowerManager.THERMAL_STATUS_LIGHT || headroom >= 0.55f -> ThermalGuardState.LIGHT
                else -> ThermalGuardState.NOMINAL
            }
            state to headroom
        } catch (_: Throwable) {
            ThermalGuardState.NOMINAL to 0.0f
        }
    }
}
