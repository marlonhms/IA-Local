package com.example.aurapostoassitance.data.local.memory

import android.content.Context
import com.example.aurapostoassitance.data.npu.AuraNpuEngine
import com.example.aurapostoassitance.data.npu.LiteRtNpuRuntime
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.util.UUID
import java.util.concurrent.locks.ReentrantReadWriteLock
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.concurrent.read
import kotlin.concurrent.write

@Serializable
data class SerializedMemoryItem(
    val id: String,
    val segment: String,
    val category: String,
    val title: String,
    val content: String,
    val embeddingCsv: String,
    val timestamp: Long
)

data class AuraMemoryItem(
    val id: String,
    val segment: String,
    val category: String, // "DECISAO_EXECUTIVA", "AUDITORIA_NPU", "SCAN_DOCUMENTO", "CHAT_INSIGHT"
    val title: String,
    val content: String,
    val embedding: FloatArray,
    val timestamp: Long
)

data class AuraMemoryMatch(
    val item: AuraMemoryItem,
    val similarity: Float,
    val latencyMs: Float
)

/**
 * Cofre de Memória Semântica Vetorial On-Device 2.0 (RAG Local na NPU).
 * - Persistência binária compacta (IEEE-754 packed floats) com escrita assíncrona debounced e atômica.
 * - Matriz vetorial contígua em RAM (cache-friendly) com proteção thread-safe via ReentrantReadWriteLock.
 * - Zero I/O na Main Thread e isolamento multi-domínio por segment/pack_id.
 */
@Singleton
class AuraSemanticMemoryVault internal constructor(
    private val storageDir: File,
    private val npuEngine: AuraNpuEngine,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    private val saveDebounceMs: Long = 400L
) {
    @Inject
    constructor(
        @ApplicationContext context: Context,
        npuEngine: AuraNpuEngine
    ) : this(context.filesDir, npuEngine, Dispatchers.IO, 400L)

    companion object {
        private const val BINARY_MAGIC = 0x41555241 // "AURA"
        private const val BINARY_VERSION = 2
        private const val MAX_MEMORIES = 500
        private const val EMBEDDING_DIM = LiteRtNpuRuntime.EMBEDDING_DIM
    }

    private val vaultScope = CoroutineScope(SupervisorJob() + ioDispatcher)
    private val rwLock = ReentrantReadWriteLock()
    private val legacyJson = Json { ignoreUnknownKeys = true; prettyPrint = false }

    private val binaryFile: File by lazy { File(storageDir, "aura_semantic_memories_v2.bin") }
    private val legacyJsonFile: File by lazy { File(storageDir, "aura_semantic_memories_v1.json") }

    private val inMemoryVault = ArrayList<AuraMemoryItem>(64)
    private var contiguousMatrix = FloatArray(0)

    @Volatile
    private var pendingSaveJob: Job? = null

    init {
        vaultScope.launch {
            loadFromDiskInternal()
        }
    }

    /**
     * Indexa uma nova memória episódica calculando o embedding via AuraNpuEngine
     * e agendando persistência binária assíncrona em background.
     */
    fun indexMemory(
        category: String,
        title: String,
        content: String,
        segment: String = "postos_redes"
    ): AuraMemoryItem {
        val vector = npuEngine.computeDenseEmbedding("$title $content")
        val item = AuraMemoryItem(
            id = "mem_" + UUID.randomUUID().toString().take(8),
            segment = segment,
            category = category,
            title = title,
            content = content,
            embedding = vector,
            timestamp = System.currentTimeMillis()
        )
        rwLock.write {
            inMemoryVault.add(0, item)
            if (inMemoryVault.size > MAX_MEMORIES) {
                inMemoryVault.removeAt(inMemoryVault.lastIndex)
            }
            rebuildContiguousMatrixLocked()
        }
        scheduleSaveToDisk()
        return item
    }

    /**
     * Busca as memórias semanticamente mais similares usando produto escalar sobre matriz contígua.
     * Thread-safe para execução concorrente em Dispatchers.Default.
     */
    fun searchMemories(
        query: String,
        segment: String? = null,
        topK: Int = 3,
        minSimilarity: Float = 0.28f
    ): List<AuraMemoryMatch> {
        val startNano = System.nanoTime()
        val queryEmbedding = npuEngine.computeDenseEmbedding(query)
        if (queryEmbedding.size != EMBEDDING_DIM) return emptyList()

        return rwLock.read {
            val count = inMemoryVault.size
            if (count == 0) return@read emptyList()

            val matrix = contiguousMatrix
            val scored = ArrayList<AuraMemoryMatch>(minOf(count, 16))
            for (i in 0 until count) {
                val item = inMemoryVault[i]
                if (segment != null && !item.segment.equals(segment, ignoreCase = true) && item.segment != "universal") {
                    continue
                }
                val offset = i * EMBEDDING_DIM
                var dot = 0.0f
                for (d in 0 until EMBEDDING_DIM) {
                    dot += queryEmbedding[d] * matrix[offset + d]
                }
                val sim = dot.coerceIn(-1.0f, 1.0f)
                if (sim >= minSimilarity) {
                    scored.add(
                        AuraMemoryMatch(
                            item = item,
                            similarity = sim,
                            latencyMs = ((System.nanoTime() - startNano) / 1_000_000f).coerceAtLeast(0.05f)
                        )
                    )
                }
            }
            scored.sortByDescending { it.similarity }
            if (scored.size > topK) scored.subList(0, topK).toList() else scored
        }
    }

    fun getAllMemories(segment: String? = null): List<AuraMemoryItem> {
        return rwLock.read {
            if (segment != null) {
                inMemoryVault.filter { it.segment.equals(segment, ignoreCase = true) || it.segment == "universal" }
            } else {
                inMemoryVault.toList()
            }
        }
    }

    private fun rebuildContiguousMatrixLocked() {
        val count = inMemoryVault.size
        val matrix = FloatArray(count * EMBEDDING_DIM)
        for (i in 0 until count) {
            val emb = inMemoryVault[i].embedding
            if (emb.size == EMBEDDING_DIM) {
                System.arraycopy(emb, 0, matrix, i * EMBEDDING_DIM, EMBEDDING_DIM)
            }
        }
        contiguousMatrix = matrix
    }

    private fun scheduleSaveToDisk() {
        pendingSaveJob?.cancel()
        pendingSaveJob = vaultScope.launch {
            if (saveDebounceMs > 0L) delay(saveDebounceMs)
            flushToDiskNow()
        }
    }

    internal fun flushToDiskNow() {
        val snapshot = rwLock.read { inMemoryVault.toList() }
        try {
            if (!storageDir.exists()) storageDir.mkdirs()
            val tmpFile = File(storageDir, "${binaryFile.name}.tmp")
            DataOutputStream(BufferedOutputStream(FileOutputStream(tmpFile))).use { out ->
                out.writeInt(BINARY_MAGIC)
                out.writeInt(BINARY_VERSION)
                out.writeInt(EMBEDDING_DIM)
                out.writeInt(snapshot.size)
                for (item in snapshot) {
                    out.writeUTF(item.id)
                    out.writeUTF(item.segment)
                    out.writeUTF(item.category)
                    out.writeUTF(item.title)
                    out.writeUTF(item.content)
                    out.writeLong(item.timestamp)
                    val vec = item.embedding
                    for (d in 0 until EMBEDDING_DIM) {
                        out.writeFloat(if (d < vec.size) vec[d] else 0f)
                    }
                }
            }
            if (binaryFile.exists()) binaryFile.delete()
            if (!tmpFile.renameTo(binaryFile)) {
                tmpFile.copyTo(binaryFile, overwrite = true)
                tmpFile.delete()
            }
        } catch (_: Exception) {
        }
    }

    internal fun loadFromDiskInternal() {
        val loaded = loadBinaryFile() ?: migrateLegacyJsonFile()
        rwLock.write {
            inMemoryVault.clear()
            if (loaded != null && loaded.isNotEmpty()) {
                inMemoryVault.addAll(loaded.take(MAX_MEMORIES))
            } else {
                seedDefaultMemoriesLocked()
            }
            rebuildContiguousMatrixLocked()
        }
        if (loaded == null || !binaryFile.exists()) {
            flushToDiskNow()
        }
    }

    private fun loadBinaryFile(): List<AuraMemoryItem>? {
        if (!binaryFile.exists() || binaryFile.length() == 0L) return null
        return runCatching {
            DataInputStream(BufferedInputStream(FileInputStream(binaryFile))).use { inp ->
                val magic = inp.readInt()
                val version = inp.readInt()
                val dim = inp.readInt()
                if (magic != BINARY_MAGIC || version != BINARY_VERSION || dim != EMBEDDING_DIM) {
                    return null
                }
                val count = inp.readInt().coerceIn(0, MAX_MEMORIES)
                val list = ArrayList<AuraMemoryItem>(count)
                for (i in 0 until count) {
                    val id = inp.readUTF()
                    val segment = inp.readUTF()
                    val category = inp.readUTF()
                    val title = inp.readUTF()
                    val content = inp.readUTF()
                    val timestamp = inp.readLong()
                    val vec = FloatArray(dim)
                    for (d in 0 until dim) {
                        vec[d] = inp.readFloat()
                    }
                    list.add(AuraMemoryItem(id, segment, category, title, content, vec, timestamp))
                }
                list
            }
        }.getOrNull()
    }

    private fun migrateLegacyJsonFile(): List<AuraMemoryItem>? {
        if (!legacyJsonFile.exists()) return null
        return runCatching {
            val raw = legacyJsonFile.readText()
            val list = legacyJson.decodeFromString<List<SerializedMemoryItem>>(raw)
            list.mapNotNull { s ->
                val floats = s.embeddingCsv.split(",").mapNotNull { it.toFloatOrNull() }.toFloatArray()
                if (floats.size == EMBEDDING_DIM) {
                    AuraMemoryItem(s.id, s.segment, s.category, s.title, s.content, floats, s.timestamp)
                } else {
                    null
                }
            }
        }.getOrNull()
    }

    private fun seedDefaultMemoriesLocked() {
        val seeds = listOf(
            Triple(
                "postos_redes",
                "Compra Fracionada Antecipada Diesel S10",
                "Aprovada compra fracionada de 15.000 L de Diesel S10 antes do fechamento de pauta da distribuidora. Economia líquida apurada de R$ 30.600,00 frente a compras emergenciais."
            ),
            Triple(
                "postos_redes",
                "Auditoria de Fuga Invisível de Margem e Descontos",
                "Identificados R$ 5.215,00/mês em desvios entre descontos manuais de pista e sangrias sem alçada. Estabelecido teto de desconto automático de R$ 0,08/L para frotistas cadastrados."
            ),
            Triple(
                "postos_redes",
                "Conformidade de LMC e Variação Térmica ANP",
                "Divergência entre régua física e telemetria Veeder-Root auditada em 0,38%, rigorosamente dentro do limite legal de 0,6% estipulado pela ANP."
            ),
            Triple(
                "postos_redes",
                "Reativação de Frotas em Risco de Churn",
                "Disparado lote com 14 frotas de frete pesado com mais de 12 dias sem abastecimento. Oferta de bonificação em Arla 32 recuperou 9 contas ativas."
            ),
            Triple(
                "universal",
                "Assinatura Criptográfica de Alçada no Silício",
                "Toda ordem executiva com impacto financeiro superior a R$ 5.000,00 requer biometria Class 3 e assinatura ECDSA no TEE/StrongBox do dispositivo."
            )
        )

        val yesterday = System.currentTimeMillis() - 86_400_000L
        seeds.forEach { (seg, tit, cont) ->
            val vec = npuEngine.computeDenseEmbedding("$tit $cont")
            inMemoryVault.add(
                AuraMemoryItem(
                    id = "seed_" + UUID.randomUUID().toString().take(6),
                    segment = seg,
                    category = "DECISAO_EXECUTIVA",
                    title = tit,
                    content = cont,
                    embedding = vec,
                    timestamp = yesterday
                )
            )
        }
    }
}
