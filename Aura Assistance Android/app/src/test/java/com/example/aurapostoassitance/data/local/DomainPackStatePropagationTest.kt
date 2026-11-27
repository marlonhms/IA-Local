package com.example.aurapostoassitance.data.local

import com.example.aurapostoassitance.data.remote.AuraApiService
import com.example.aurapostoassitance.data.remote.AuraIntelligenceRepository
import com.example.aurapostoassitance.data.remote.BacktestRunRequestDto
import com.example.aurapostoassitance.data.remote.BacktestRunResponseDto
import com.example.aurapostoassitance.data.remote.HandoffMarkReadResponse
import com.example.aurapostoassitance.data.remote.HandoffRequest
import com.example.aurapostoassitance.data.remote.HandoffResponse
import com.example.aurapostoassitance.data.remote.HandoffThreadsResponse
import com.example.aurapostoassitance.data.remote.HealthResponse
import com.example.aurapostoassitance.data.remote.IntentRequest
import com.example.aurapostoassitance.data.remote.IntentResponse
import com.example.aurapostoassitance.data.remote.MemoryGovernanceFeedResponseDto
import com.example.aurapostoassitance.data.remote.MemoryRuleListResponseDto
import com.example.aurapostoassitance.data.remote.MonteCarloBandsDto
import com.example.aurapostoassitance.data.remote.MorningBriefingRequest
import com.example.aurapostoassitance.data.remote.MorningBriefingResponse
import com.example.aurapostoassitance.data.remote.QuickActionRequest
import com.example.aurapostoassitance.data.remote.QuickActionResponse
import com.example.aurapostoassitance.data.remote.RealizedRoiScorecardResponseDto
import com.example.aurapostoassitance.data.remote.RuleDecisionRequestDto
import com.example.aurapostoassitance.data.remote.RuleDecisionResponseDto
import com.example.aurapostoassitance.data.remote.SegmentBaselineResponse
import com.example.aurapostoassitance.data.remote.SimulationRecomputeRequestDto
import com.example.aurapostoassitance.data.remote.SimulationRecomputeResponseDto
import com.example.aurapostoassitance.data.remote.WhatIfSimulateRequest
import com.example.aurapostoassitance.data.remote.WhatIfSimulateResponse
import com.example.aurapostoassitance.data.remote.ZeroClickFeedResponse
import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test

class DomainPackStatePropagationTest {

    private class FakeAuraApiService(
        private val responsePackId: String
    ) : AuraApiService {
        override suspend fun checkHealth(): HealthResponse = HealthResponse(status = "healthy")

        override suspend fun getZeroClickFeed(packId: String?): ZeroClickFeedResponse =
            ZeroClickFeedResponse(success = true, pack_id = responsePackId)

        override suspend fun simulateWhatIf(request: WhatIfSimulateRequest): WhatIfSimulateResponse =
            WhatIfSimulateResponse()

        override suspend fun getStations(): String = "[]"
        override suspend fun executeIntent(request: IntentRequest): IntentResponse = IntentResponse("ok")
        override suspend fun getSegmentBaseline(segment: String): SegmentBaselineResponse =
            SegmentBaselineResponse(segment = segment)
        override suspend fun getMorningBriefing(request: MorningBriefingRequest): MorningBriefingResponse =
            MorningBriefingResponse()
        override suspend fun executeQuickAction(request: QuickActionRequest): QuickActionResponse =
            QuickActionResponse()
        override suspend fun executeStationQuickAction(stationId: String, request: QuickActionRequest): QuickActionResponse =
            QuickActionResponse()
        override suspend fun triggerHandoff(request: HandoffRequest): HandoffResponse = HandoffResponse()
        override suspend fun getHandoffThreads(syncEvolution: Boolean, limit: Int): HandoffThreadsResponse =
            HandoffThreadsResponse()
        override suspend fun markHandoffThreadRead(phone: String): HandoffMarkReadResponse =
            HandoffMarkReadResponse()

        override suspend fun recomputeSimulation(request: SimulationRecomputeRequestDto): SimulationRecomputeResponseDto =
            SimulationRecomputeResponseDto(
                simulation_id = "sim_1",
                tenant_id = request.tenant_id,
                pack_id = responsePackId,
                scenario_type = request.scenario_type,
                horizon_days = request.horizon_days,
                monte_carlo = MonteCarloBandsDto(100.0, 200.0, 300.0, 200.0, 40.0, 95.0, 5000, 42),
                is_compliant = true,
                elapsed_ms = 12.0
            )

        override suspend fun listMemoryRules(packId: String, tenantId: String, status: String?): MemoryRuleListResponseDto =
            MemoryRuleListResponseDto(tenant_id = tenantId, pack_id = responsePackId, total = 0)

        override suspend fun getMemorySuggestions(packId: String, tenantId: String, windowDays: Int, minHits: Int): MemoryGovernanceFeedResponseDto =
            MemoryGovernanceFeedResponseDto(tenant_id = tenantId, pack_id = responsePackId)

        override suspend fun decideMemoryRule(ruleId: String, request: RuleDecisionRequestDto): RuleDecisionResponseDto =
            throw UnsupportedOperationException()

        override suspend fun runBacktest(request: BacktestRunRequestDto): BacktestRunResponseDto =
            BacktestRunResponseDto(tenant_id = request.tenant_id, pack_id = responsePackId, evaluated_count = 0)

        override suspend fun getBacktestScorecard(packId: String, tenantId: String, limit: Int): RealizedRoiScorecardResponseDto =
            RealizedRoiScorecardResponseDto(tenant_id = tenantId, pack_id = responsePackId)
    }

    @Test
    fun `updates StateFlow reactively across all domain packs and normalizes legacy aliases`() {
        val holder = DomainPackStateHolder()
        assertEquals(AuraDomainAdapter.PACK_FUEL, holder.activePackId.value)

        holder.updatePackId("saude_clinicas")
        assertEquals(AuraDomainAdapter.PACK_PHARMACY, holder.activePackId.value)

        holder.updatePackId("retail_supermarket")
        assertEquals(AuraDomainAdapter.PACK_RETAIL, holder.activePackId.value)

        holder.updatePackId("autocenter_parts")
        assertEquals(AuraDomainAdapter.PACK_AUTOCENTER, holder.activePackId.value)

        holder.updatePackId("wholesale_distribution")
        assertEquals(AuraDomainAdapter.PACK_WHOLESALE, holder.activePackId.value)

        // Valores nulos ou em branco preservam o domínio ativo sem voltar para posto
        holder.updatePackId("   ")
        assertEquals(AuraDomainAdapter.PACK_WHOLESALE, holder.activePackId.value)
    }

    @Test
    fun `repository propagates pack_id returned by backend into reactive StateFlow`() = runBlocking {
        val holder = DomainPackStateHolder()
        val syncedCallbacks = mutableListOf<String>()
        val repo = AuraIntelligenceRepository(
            apiService = FakeAuraApiService(responsePackId = "pharmacy_health"),
            domainPackStateHolder = holder,
            tenantIdProvider = { "farmacia_01" },
            onPackIdSynced = { syncedCallbacks.add(it) }
        )

        assertEquals(AuraDomainAdapter.PACK_FUEL, repo.activePackId.value)

        repo.getBacktestScorecard()

        assertEquals("pharmacy_health", repo.activePackId.value)
        assertEquals(listOf("pharmacy_health"), syncedCallbacks)
    }
}
