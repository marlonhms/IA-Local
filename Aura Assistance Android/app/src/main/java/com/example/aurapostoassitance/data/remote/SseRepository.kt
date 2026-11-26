package com.example.aurapostoassitance.data.remote

import android.util.Log
import com.example.aurapostoassitance.data.local.ServerConfig
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull
import kotlinx.serialization.json.put
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import javax.inject.Inject

/**
 * Parser puro e testável de chunks SSE do protocolo Carbon Core (P0.3 / P0.4 / P1.3).
 */
object SseChunkParser {

    private val defaultJson = Json { ignoreUnknownKeys = true; isLenient = true }

    fun parse(type: String?, data: String, json: Json = defaultJson): SseEvent? {
        if (data.isBlank() || data == "[DONE]") return null
        return try {
            val jsonObj = json.parseToJsonElement(data).jsonObject
            val chunkType = (type?.takeIf { it.isNotBlank() }
                ?: jsonObj["chunk_type"]?.jsonPrimitive?.contentOrNull
                ?: "").lowercase()

            when (chunkType) {
                "intent" -> {
                    val intentName = jsonObj.str("text")
                        ?: (jsonObj["data"] as? JsonObject)?.str("intent")
                        ?: "analisando"
                    val friendlyName = friendlyIntentName(intentName)
                    SseEvent.StatusUpdate("SQL Read-Only • $friendlyName")
                }
                "tool_start" -> {
                    val msg = jsonObj.str("text")
                        ?: (jsonObj["data"] as? JsonObject)?.str("label")
                        ?: "Consultando base operacional Read-Only..."
                    SseEvent.StatusUpdate(msg)
                }
                "tool_result" -> {
                    val summary = jsonObj.str("text") ?: "Cálculo Python determinístico auditado"
                    SseEvent.ToolResult(summary)
                }
                "cache_hit" -> {
                    val label = jsonObj.str("text") ?: "Cache Semântico Local (0 tokens)"
                    SseEvent.CacheHit(label)
                }
                "ui_skeleton" -> {
                    val payload = (jsonObj["data"] as? JsonObject) ?: jsonObj
                    val toolCallId = payload.str("tool_call_id") ?: "slot_${System.currentTimeMillis()}"
                    val component = payload.str("component_name") ?: payload.str("client_component") ?: "GenUI"
                    val title = payload.str("title")
                    SseEvent.UiSkeleton(toolCallId = toolCallId, componentName = component, title = title)
                }
                "ui_delta" -> {
                    val payload = (jsonObj["data"] as? JsonObject) ?: jsonObj
                    val toolCallId = payload.str("tool_call_id") ?: "slot_active"
                    SseEvent.UiDelta(toolCallId = toolCallId, partialJson = payload.toString())
                }
                "ui_complete" -> {
                    val envelope = jsonObj["envelope"]?.takeIf { it is JsonObject }
                        ?: jsonObj["data"]?.takeIf { it is JsonObject }
                    envelope?.let { SseEvent.UiComplete(it.toString()) }
                }
                "telemetry" -> {
                    val payload = (jsonObj["data"] as? JsonObject) ?: jsonObj
                    SseEvent.Telemetry(
                        ttftMs = payload.long("ttft_ms"),
                        totalMs = payload.long("total_ms") ?: payload.long("latency_ms"),
                        piiRedactedCount = payload.int("pii_redacted_count")
                            ?: payload.int("lgpd_redacted")
                            ?: 0,
                        sourceLabel = payload.str("source") ?: payload.str("data_source"),
                        cacheHit = payload.bool("cache_hit") ?: false
                    )
                }
                "stream_reset" -> SseEvent.StreamReset
                "delta" -> {
                    val textDelta = jsonObj.str("text")
                    if (!textDelta.isNullOrEmpty()) SseEvent.TextDelta(textDelta) else null
                }
                "error" -> {
                    val errMsg = jsonObj.str("text") ?: "Erro no processamento"
                    SseEvent.Error(errMsg)
                }
                "done" -> SseEvent.Done
                else -> {
                    val textDelta = jsonObj.str("text")
                    val isInternalChunk = chunkType.startsWith("ui_") || chunkType == "ping" || chunkType == "heartbeat"
                    if (!textDelta.isNullOrEmpty() && !isInternalChunk) {
                        SseEvent.TextDelta(textDelta)
                    } else null
                }
            }
        } catch (_: Exception) {
            if (data.isNotBlank() && data != "[DONE]") SseEvent.TextDelta(data) else null
        }
    }

    private fun friendlyIntentName(intentName: String): String = when (intentName) {
        "auditoria_turno", "auditoria_turno_caixa" -> "Conciliação de Turno"
        "previsao_tanques", "previsao_runout_estoque" -> "Previsão de Ruptura & Autonomia"
        "desempenho_pista_frentistas" -> "Desempenho Operacional"
        "lmc_anp" -> "Conformidade LMC ANP"
        "conformidade_sngpc_anvisa" -> "Conformidade SNGPC"
        "fechamento_caixa_pbm" -> "Fechamento PBM/Caixa"
        "conveniencia_vendas_cruzadas", "market_basket_cross_sell" -> "Análise de Cesta & Cross-Sell"
        "simular_cenario_what_if" -> "Simulador What-If"
        "ajuda_sistema" -> "Atendimento AURA"
        else -> intentName.replace("_", " ").replaceFirstChar { it.uppercase() }
    }

    private fun JsonObject.str(key: String): String? =
        (this[key] as? JsonPrimitive)?.contentOrNull?.takeIf { it.isNotBlank() && it != "null" }

    private fun JsonObject.int(key: String): Int? =
        (this[key] as? JsonPrimitive)?.intOrNull

    private fun JsonObject.long(key: String): Long? =
        (this[key] as? JsonPrimitive)?.longOrNull

    private fun JsonObject.bool(key: String): Boolean? =
        (this[key] as? JsonPrimitive)?.booleanOrNull
}

class SseRepository @Inject constructor(
    private val okHttpClient: OkHttpClient,
    private val json: Json,
    private val serverConfig: ServerConfig
) {
    fun streamChat(
        query: String,
        sessionId: String = "android_session",
        voiceMode: Boolean = false,
        packId: String = serverConfig.activePackId,
        npuIntentHint: String? = null,
        edgeRagContext: String? = null
    ): Flow<SseEvent> = callbackFlow {

        val wireQuery = if (voiceMode) {
            "[CONVERSA POR VOZ NO CARRO - fale de forma leve e informal como sócia próxima em 2 a 3 frases curtas, ZERO listas, ZERO tópicos e ZERO markdown] $query"
        } else {
            query
        }

        val jsonBody = buildJsonObject {
            put("query", wireQuery)
            put("session_id", sessionId)
            put("stream", true)
            put("tenant_id", serverConfig.tenantId)
            put("filial_id", serverConfig.filialId)
            put("pack_id", packId)
            if (voiceMode) {
                put("genui", false)
            }
            if (voiceMode || !npuIntentHint.isNullOrBlank() || !edgeRagContext.isNullOrBlank()) {
                put(
                    "context",
                    buildJsonObject {
                        if (voiceMode) {
                            put("channel", "voice_hands_free_driving")
                            put(
                                "estilo_resposta",
                                "MODO CONVERSA FLUIDA POR VOZ (DIRIGINDO). O usuário está conversando por áudio, possivelmente no carro. NÃO gere relatório formal, NÃO use tópicos, listas, tabelas, emojis ou markdown pesado. Fale como uma sócia executiva próxima em 2 a 4 frases curtas fáceis de ouvir."
                            )
                        }
                        if (!npuIntentHint.isNullOrBlank()) {
                            put("npu_intent_hint", npuIntentHint)
                        }
                        if (!edgeRagContext.isNullOrBlank()) {
                            put("edge_rag_context", edgeRagContext)
                        }
                    }
                )
            }
        }.toString()

        val chatUrl = "${serverConfig.getBaseUrl()}api/v1/aura/chat"

        val request = Request.Builder()
            .url(chatUrl)
            .addHeader("Accept", "text/event-stream")
            .post(jsonBody.toRequestBody("application/json".toMediaType()))
            .build()

        val eventSourceFactory = EventSources.createFactory(okHttpClient)

        val eventSourceListener = object : EventSourceListener() {
            override fun onOpen(eventSource: EventSource, response: Response) {
                Log.d("SSE", "Connection Opened")
                trySend(SseEvent.StatusUpdate("Filtro LGPD & PII Ativo"))
            }

            override fun onEvent(eventSource: EventSource, id: String?, type: String?, data: String) {
                Log.d("SSE", "Received event type: '$type'")
                SseChunkParser.parse(type = type, data = data, json = json)?.let { parsed ->
                    trySend(parsed)
                }
            }

            override fun onClosed(eventSource: EventSource) {
                Log.d("SSE", "Connection Closed")
                close()
            }

            override fun onFailure(eventSource: EventSource, t: Throwable?, response: Response?) {
                val errorMsg = when {
                    response?.code == 401 -> "Autenticação exigida (HTTP 401). Configure sua X-API-Key em Servidor."
                    t != null -> t.message
                    response != null -> "Erro do servidor AURA (HTTP ${response.code})"
                    else -> "Falha na conexão SSE"
                }
                Log.e("SSE", "Error: $errorMsg")
                if (t is java.io.IOException) {
                    close(t)
                } else {
                    trySend(SseEvent.Error(errorMsg ?: "Falha na conexão"))
                    close(t ?: Exception(errorMsg))
                }
            }
        }

        val eventSource = eventSourceFactory.newEventSource(request, eventSourceListener)

        awaitClose {
            eventSource.cancel()
        }
    }
}
