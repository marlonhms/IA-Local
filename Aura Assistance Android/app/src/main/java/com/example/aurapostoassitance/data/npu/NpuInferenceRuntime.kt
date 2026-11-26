package com.example.aurapostoassitance.data.npu

import android.content.Context
import android.os.Build
import android.util.Log
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.tensorflow.lite.Delegate
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.GpuDelegate
import org.tensorflow.lite.nnapi.NnApiDelegate
import java.io.File
import java.io.FileInputStream
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import java.util.concurrent.atomic.AtomicReference
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Contrato plugável de execução neural on-device (desacoplado via Hilt para testabilidade JVM).
 */
interface NpuInferenceRuntime {
    val embeddingDimension: Int
    fun activeDelegate(): NpuDelegateType
    fun isModelLoaded(): Boolean
    suspend fun warmUp(): NpuDelegateType
    fun embed(normalizedText: String, tokens: List<String>, intentScores: FloatArray): FloatArray
    fun release()
}

/**
 * Runtime híbrido baseado em Google AI Edge LiteRT (Opção A):
 * - Tier 1: Carrega modelo quantizado `.tflite` sob demanda (`filesDir/npu_models/aura_embed_int8.tflite`)
 *   com cache de compilação em `codeCacheDir/npu_cache` e fallback automático NNAPI/Hexagon -> GPU -> XNNPACK.
 * - Tier 2: Fast-Path vetorial determinístico otimizado (zero alocação de Regex) enquanto o modelo não estiver baixado
 *   ou sob proteção térmica severa.
 */
@Singleton
class LiteRtNpuRuntime @Inject constructor(
    @param:ApplicationContext private val context: Context,
    private val capabilityProbe: NpuCapabilityProbe
) : NpuInferenceRuntime {

    companion object {
        private const val TAG = "LiteRtNpuRuntime"
        const val MODEL_DIR_NAME = "npu_models"
        const val EMBEDDING_MODEL_FILE = "aura_embed_int8.tflite"
        const val EMBEDDING_DIM = 128
        private const val MAX_SEQ_TOKENS = 64
        private val PT_STOPWORDS = setOf(
            "de", "do", "da", "dos", "das", "o", "a", "os", "as", "um", "uma",
            "e", "ou", "em", "no", "na", "nos", "nas", "para", "por", "com",
            "que", "se", "eu", "me", "te", "ele", "ela", "isso", "isto", "esse", "esta"
        )
    }

    override val embeddingDimension: Int = EMBEDDING_DIM

    private val initMutex = Mutex()
    private val activeDelegateRef = AtomicReference(NpuDelegateType.FAST_PATH_VECTOR)

    @Volatile
    private var interpreter: Interpreter? = null

    @Volatile
    private var activeHardwareDelegate: Delegate? = null

    @Volatile
    private var modelLoadedFlag: Boolean = false

    override fun activeDelegate(): NpuDelegateType = activeDelegateRef.get()

    override fun isModelLoaded(): Boolean = modelLoadedFlag

    fun getModelFile(): File {
        val dir = File(context.filesDir, MODEL_DIR_NAME).apply { if (!exists()) mkdirs() }
        return File(dir, EMBEDDING_MODEL_FILE)
    }

    override suspend fun warmUp(): NpuDelegateType = withContext(Dispatchers.Default) {
        initMutex.withLock {
            if (interpreter != null) return@withLock activeDelegateRef.get()

            val profile = capabilityProbe.probeHardware()
            val modelFile = getModelFile()
            if (!modelFile.exists() || modelFile.length() == 0L) {
                activeDelegateRef.set(NpuDelegateType.FAST_PATH_VECTOR)
                modelLoadedFlag = false
                return@withLock activeDelegateRef.get()
            }

            val modelBuffer = runCatching { mapModelFile(modelFile) }.getOrNull()
            if (modelBuffer == null) {
                activeDelegateRef.set(NpuDelegateType.FAST_PATH_VECTOR)
                modelLoadedFlag = false
                return@withLock activeDelegateRef.get()
            }

            val cacheDir = File(context.codeCacheDir, "npu_cache").apply { if (!exists()) mkdirs() }

            // Ordem de tentativa respeitando governança térmica e disponibilidade de silício
            val candidates = buildList {
                if (profile.thermalState.allowNpuOffload) {
                    if (profile.hasDedicatedNpu && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        add(NpuDelegateType.NNAPI_NPU)
                    }
                    add(NpuDelegateType.GPU_DELEGATE)
                }
                add(NpuDelegateType.CPU_XNNPACK)
            }

            for (candidate in candidates) {
                val created = tryCreateInterpreter(
                    modelBuffer = modelBuffer,
                    delegateType = candidate,
                    threads = profile.maxRecommendedThreads,
                    cacheDir = cacheDir
                )
                if (created != null) {
                    interpreter = created.first
                    activeHardwareDelegate = created.second
                    activeDelegateRef.set(candidate)
                    modelLoadedFlag = true
                    Log.i(TAG, "LiteRT inicializado com sucesso em ${candidate.label} (${profile.marketingName})")
                    return@withLock candidate
                }
            }

            activeDelegateRef.set(NpuDelegateType.FAST_PATH_VECTOR)
            modelLoadedFlag = false
            activeDelegateRef.get()
        }
    }

    private fun tryCreateInterpreter(
        modelBuffer: MappedByteBuffer,
        delegateType: NpuDelegateType,
        threads: Int,
        cacheDir: File
    ): Pair<Interpreter, Delegate?>? {
        var delegate: Delegate? = null
        return try {
            val options = Interpreter.Options().apply {
                setNumThreads(threads)
                setUseXNNPACK(true)
            }
            when (delegateType) {
                NpuDelegateType.NNAPI_NPU -> {
                    val nnOpts = NnApiDelegate.Options().apply {
                        setExecutionPreference(NnApiDelegate.Options.EXECUTION_PREFERENCE_SUSTAINED_SPEED)
                        setCacheDir(cacheDir.absolutePath)
                        setModelToken("aura_embed_v1")
                        setAllowFp16(true)
                    }
                    delegate = NnApiDelegate(nnOpts)
                    options.addDelegate(delegate)
                }
                NpuDelegateType.GPU_DELEGATE -> {
                    delegate = GpuDelegate()
                    options.addDelegate(delegate)
                }
                NpuDelegateType.CPU_XNNPACK,
                NpuDelegateType.FAST_PATH_VECTOR -> Unit
            }
            Interpreter(modelBuffer, options) to delegate
        } catch (t: Throwable) {
            Log.w(TAG, "Fallback ao inicializar delegate ${delegateType.label}: ${t.message}")
            runCatching { delegate?.close() }
            null
        }
    }

    private fun mapModelFile(file: File): MappedByteBuffer {
        FileInputStream(file).use { fis ->
            val channel = fis.channel
            return channel.map(FileChannel.MapMode.READ_ONLY, 0, channel.size())
        }
    }

    override fun embed(normalizedText: String, tokens: List<String>, intentScores: FloatArray): FloatArray {
        val currentInterpreter = interpreter
        if (currentInterpreter != null) {
            val (thermalState, _) = capabilityProbe.readThermalGuard()
            if (thermalState.allowNpuOffload || activeDelegateRef.get() == NpuDelegateType.CPU_XNNPACK) {
                val neural = runLiteRtEmbedding(currentInterpreter, tokens)
                if (neural != null) return neural
            }
        }
        return computeFastPathEmbedding(tokens, intentScores)
    }

    private fun runLiteRtEmbedding(activeInterpreter: Interpreter, tokens: List<String>): FloatArray? {
        return try {
            val inputIds = Array(1) { IntArray(MAX_SEQ_TOKENS) }
            val limit = minOf(tokens.size, MAX_SEQ_TOKENS)
            for (i in 0 until limit) {
                inputIds[0][i] = (abs(tokens[i].hashCode()) % 30000) + 1
            }
            val output = Array(1) { FloatArray(EMBEDDING_DIM) }
            synchronized(activeInterpreter) {
                activeInterpreter.run(inputIds, output)
            }
            normalizeL2(output[0])
            output[0]
        } catch (t: Throwable) {
            Log.w(TAG, "Erro durante inferência LiteRT, usando Fast-Path: ${t.message}")
            null
        }
    }

    /**
     * Projeção densa determinística de 128d com filtragem de stopwords PT-BR,
     * trigramas morfológicos e sinalização de âncoras de intenção já pré-pontuadas.
     */
    private fun computeFastPathEmbedding(tokens: List<String>, intentScores: FloatArray): FloatArray {
        val vector = FloatArray(EMBEDDING_DIM)

        for (word in tokens) {
            if (word.length < 2 || word in PT_STOPWORDS) continue
            val hash = word.hashCode()
            val idx1 = (hash and 0x7FFFFFFF) % EMBEDDING_DIM
            val idx2 = (hash.ushr(7) and 0x7FFFFFFF) % EMBEDDING_DIM
            vector[idx1] += if (hash and 1 == 0) 1.5f else -1.5f
            vector[idx2] += if (hash and 2 == 0) 1.0f else -1.0f

            if (word.length >= 3) {
                val maxTri = word.length - 3
                for (i in 0..maxTri) {
                    val triHash = ((word[i].code * 31 + word[i + 1].code) * 31 + word[i + 2].code)
                    val triIdx = (triHash and 0x7FFFFFFF) % EMBEDDING_DIM
                    vector[triIdx] += if (triHash and 1 == 0) 0.6f else -0.6f
                }
            }
        }

        // Injeta os scores de intenção já computados sem re-escanear todas as âncoras
        for (intentOrdinal in intentScores.indices) {
            val score = intentScores[intentOrdinal]
            if (score > 0f) {
                val baseOffset = (intentOrdinal * 16) % EMBEDDING_DIM
                val scaled = score * 0.9f
                for (k in 0..3) {
                    vector[(baseOffset + k) % EMBEDDING_DIM] += scaled
                }
            }
        }

        normalizeL2(vector)
        return vector
    }

    private fun normalizeL2(vector: FloatArray) {
        var normSq = 0.0f
        for (i in vector.indices) {
            val v = vector[i]
            normSq += v * v
        }
        val norm = sqrt(normSq)
        if (norm > 1e-6f) {
            val invNorm = 1.0f / norm
            for (i in vector.indices) {
                vector[i] *= invNorm
            }
        }
    }

    override fun release() {
        runCatching { interpreter?.close() }
        runCatching { activeHardwareDelegate?.close() }
        interpreter = null
        activeHardwareDelegate = null
        modelLoadedFlag = false
        activeDelegateRef.set(NpuDelegateType.FAST_PATH_VECTOR)
    }
}
