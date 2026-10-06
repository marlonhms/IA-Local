package com.example.aurapostoassitance.data.remote

import kotlinx.serialization.Serializable
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Body

@Serializable
data class HealthResponse(
    val status: String,
    val components: Map<String, String>? = null
)

@Serializable
data class IntentRequest(
    val intent: String,
    val parameters: Map<String, String> = emptyMap()
)

@Serializable
data class IntentResponse(
    val result: String,
    val data: Map<String, String>? = null
)

interface AuraApiService {

    @GET("api/v1/aura/health")
    suspend fun checkHealth(): HealthResponse

    @GET("api/v1/aura/stations")
    suspend fun getStations(): String // Placeholder response

    @POST("api/v1/aura/execute-intent")
    suspend fun executeIntent(@Body request: IntentRequest): IntentResponse
}
