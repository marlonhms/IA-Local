package com.example.aurapostoassitance.data.remote

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

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

@Serializable
data class BriefingActionDto(
    val code: String,
    val label: String,
    val description: String? = null
)

@Serializable
data class MorningBriefingRequest(
    val segment: String = "postos_redes",
    val manager_name: String? = "Marlon Henrique",
    val business_name: String? = null,
    val station_id: String? = "posto_01",
    val manager_phone: String? = null
)

@Serializable
data class MorningBriefingResponse(
    val success: Boolean = true,
    val segment: String = "postos_redes",
    val managerName: String? = null,
    val businessName: String? = null,
    val oralVoiceScript: String = "",
    val whatsappExecutiveText: String = "",
    val suggestedActions: List<BriefingActionDto> = emptyList(),
    val genUiCard: JsonObject? = null
)

@Serializable
data class QuickActionRequest(
    val action_type: String = "PROGRAMAR_PEDIDO_COMBUSTIVEL",
    val option_key: String,
    val voucher_id: String? = null,
    val actor_phone: String? = null,
    val actor_name: String = "Marlon Henrique",
    val parameters: Map<String, String> = emptyMap()
)

@Serializable
data class QuickActionResponse(
    val success: Boolean = true,
    val action_executed: String? = null,
    val option_key: String? = null,
    val station_id: String? = null,
    val voucher_id: String? = null,
    val journal_id: String? = null,
    val status: String? = null,
    val confirmation_text: String? = null,
    val replayed: Boolean? = false,
    val timestamp: String? = null
)

@Serializable
data class HandoffRequest(
    val action_id: String,
    val segment: String = "postos_redes",
    val phone: String,
    val contact_name: String? = null,
    val initial_message: String,
    val session_handoff_context: String,
    val station_id: String = "posto_01",
    val attachment_base64: String? = null,
    val attachment_mimetype: String? = null,
    val attachment_filename: String? = null,
    val attachment_caption: String? = null
)

@Serializable
data class HandoffResponse(
    val success: Boolean = true,
    val status: String? = null,
    val whatsapp_sent: Boolean? = null,
    val media_sent: Boolean? = null,
    val command_key: String? = null,
    val journal_id: String? = null,
    val session_handoff_context: String? = null,
    val confirmation_text: String? = null
)

@Serializable
data class SegmentBaselineResponse(
    val success: Boolean = true,
    val segment: String,
    val profile: Map<String, String>? = null,
    val sampleBusinessName: String? = null,
    val sampleManagerName: String? = null,
    val samplePhone: String? = null,
    val runOutTelemetry: JsonObject? = null,
    val leakageTelemetry: JsonObject? = null,
    val rfmTelemetry: JsonObject? = null,
    val genUiCards: JsonObject? = null
)

interface AuraApiService {

    @GET("api/v1/aura/health")
    suspend fun checkHealth(): HealthResponse

    @GET("api/v1/aura/stations")
    suspend fun getStations(): String

    @POST("api/v1/aura/execute-intent")
    suspend fun executeIntent(@Body request: IntentRequest): IntentResponse

    @GET("api/v1/partner/segments/{segment}/baseline")
    suspend fun getSegmentBaseline(@Path("segment") segment: String): SegmentBaselineResponse

    @POST("api/v1/partner/morning-briefing")
    suspend fun getMorningBriefing(@Body request: MorningBriefingRequest): MorningBriefingResponse

    @POST("api/v1/partner/quick-actions")
    suspend fun executeQuickAction(@Body request: QuickActionRequest): QuickActionResponse

    @POST("api/v1/partner/stations/{station_id}/quick-action")
    suspend fun executeStationQuickAction(
        @Path("station_id") stationId: String,
        @Body request: QuickActionRequest
    ): QuickActionResponse

    @POST("api/v1/partner/handoff")
    suspend fun triggerHandoff(@Body request: HandoffRequest): HandoffResponse
}
