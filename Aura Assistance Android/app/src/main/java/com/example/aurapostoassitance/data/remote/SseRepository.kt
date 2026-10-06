package com.example.aurapostoassitance.data.remote

import android.util.Log
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import com.example.aurapostoassitance.data.local.ServerConfig
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import javax.inject.Inject

class SseRepository @Inject constructor(
    private val okHttpClient: OkHttpClient,
    private val json: Json,
    private val serverConfig: ServerConfig
) {
    fun streamChat(query: String, sessionId: String = "android_session"): Flow<SseEvent> = callbackFlow {
        
        val jsonBody = """
            {
                "query": "$query",
                "session_id": "$sessionId",
                "stream": true,
                "tenant_id": "posto_01",
                "filial_id": "59050"
            }
        """.trimIndent()
        
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
                trySend(SseEvent.StatusUpdate("⚡ Conectado à AURA, processando..."))
            }

            override fun onEvent(eventSource: EventSource, id: String?, type: String?, data: String) {
                Log.d("SSE", "Received event type: '$type', data: $data")
                try {
                    val jsonObj = json.parseToJsonElement(data).jsonObject
                    val chunkType = type ?: jsonObj["chunk_type"]?.jsonPrimitive?.content ?: ""
                    
                    when (chunkType) {
                        "intent" -> {
                            val intentName = jsonObj["text"]?.jsonPrimitive?.content 
                                ?: jsonObj["data"]?.jsonObject?.get("intent")?.jsonPrimitive?.content 
                                ?: "analisando"
                            val friendlyName = when (intentName) {
                                "auditoria_turno" -> "Auditoria de Turno"
                                "previsao_tanques" -> "Previsão de Tanques"
                                "desempenho_pista_frentistas" -> "Desempenho da Pista"
                                "lmc_anp" -> "Relatório LMC ANP"
                                "conveniencia_vendas_cruzadas" -> "Vendas da Conveniência"
                                "ajuda_sistema" -> "Atendimento AURA"
                                else -> intentName
                            }
                            trySend(SseEvent.StatusUpdate("🎯 Roteando para: $friendlyName..."))
                        }
                        "tool_start" -> {
                            val msg = jsonObj["text"]?.jsonPrimitive?.content ?: "Executando ferramenta do posto..."
                            trySend(SseEvent.StatusUpdate("⚙️ $msg"))
                        }
                        "delta" -> {
                            val textDelta = jsonObj["text"]?.jsonPrimitive?.content
                            if (!textDelta.isNullOrEmpty()) {
                                trySend(SseEvent.TextDelta(textDelta))
                            }
                        }
                        "error" -> {
                            val errMsg = jsonObj["text"]?.jsonPrimitive?.content ?: "Erro no processamento"
                            trySend(SseEvent.Error(errMsg))
                        }
                        "done" -> {
                            trySend(SseEvent.Done)
                        }
                        else -> {
                            val textDelta = jsonObj["text"]?.jsonPrimitive?.content
                            if (!textDelta.isNullOrEmpty() && chunkType != "telemetry" && chunkType != "cache_hit" && chunkType != "tool_result") {
                                trySend(SseEvent.TextDelta(textDelta))
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.e("SSE", "Failed to parse chunk JSON: ${e.message}")
                    if (data.isNotBlank() && data != "[DONE]") {
                        trySend(SseEvent.TextDelta(data))
                    }
                }
            }

            override fun onClosed(eventSource: EventSource) {
                Log.d("SSE", "Connection Closed")
                close()
            }

            override fun onFailure(eventSource: EventSource, t: Throwable?, response: Response?) {
                Log.e("SSE", "Error: ${t?.message}")
                close(t)
            }
        }

        val eventSource = eventSourceFactory.newEventSource(request, eventSourceListener)

        awaitClose {
            eventSource.cancel()
        }
    }
}
