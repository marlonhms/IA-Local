package com.example.aurapostoassitance.ui.intelligence

import com.example.aurapostoassitance.data.local.DomainPackStateHolder
import com.example.aurapostoassitance.data.remote.AuraApiService
import com.example.aurapostoassitance.data.remote.AuraIntelligenceRepository
import com.example.aurapostoassitance.data.remote.BacktestItemResultDto
import com.example.aurapostoassitance.data.remote.BacktestRunRequestDto
import com.example.aurapostoassitance.data.remote.BacktestRunResponseDto
import com.example.aurapostoassitance.data.remote.BusinessRuleDto
import com.example.aurapostoassitance.data.remote.CalibrationProposalDto
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
import com.example.aurapostoassitance.data.remote.RuleViolationDto
import com.example.aurapostoassitance.data.remote.SegmentBaselineResponse
import com.example.aurapostoassitance.data.remote.ShockVectorDto
import com.example.aurapostoassitance.data.remote.SimulationProvenanceDto
import com.example.aurapostoassitance.data.remote.SimulationRecomputeRequestDto
import com.example.aurapostoassitance.data.remote.SimulationRecomputeResponseDto
import com.example.aurapostoassitance.data.remote.SuggestedSimulationCardDto
import com.example.aurapostoassitance.data.remote.WhatIfSimulateRequest
import com.example.aurapostoassitance.data.remote.WhatIfSimulateResponse
import com.example.aurapostoassitance.data.remote.ZeroClickFeedResponse
import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import com.example.aurapostoassitance.ui.genui.isTankTileAllowedForPack
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Collections

class AuraIntelligenceViewModelTest {

    private val testScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private suspend fun awaitUntil(timeoutMs: Long = 1500L, condition: () -> Boolean) {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (!condition() && System.currentTimeMillis() < deadline) {
            delay(10)
        }
    }

    @After
    fun tearDown() {
        testScope.cancel()
    }

    private class RecordingFakeApiService : AuraApiService {
        val recomputeRequests: MutableList<SimulationRecomputeRequestDto> =
            Collections.synchronizedList(mutableListOf())
        val ruleDecisions: MutableList<Pair<String, RuleDecisionRequestDto>> =
            Collections.synchronizedList(mutableListOf())
        var packId = AuraDomainAdapter.PACK_RETAIL

        override suspend fun checkHealth(): HealthResponse = HealthResponse("healthy")
        override suspend fun getZeroClickFeed(packId: String?): ZeroClickFeedResponse =
            ZeroClickFeedResponse(success = true, pack_id = packId ?: this.packId)
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

        override suspend fun recomputeSimulation(request: SimulationRecomputeRequestDto): SimulationRecomputeResponseDto {
            recomputeRequests.add(request)
            val violations = if (request.shocks.discount_pct > 10.0) {
                listOf(
                    RuleViolationDto(
                        rule_id = "rule_disc_cap",
                        source = "business_memory",
                        rule_key = "teto_desconto",
                        metric = "discount_pct",
                        operator = "<=",
                        threshold = 10.0,
                        observed_value = request.shocks.discount_pct,
                        severity = "CRITICAL",
                        message = "Desconto excede o teto de 10%."
                    )
                )
            } else emptyList()

            return SimulationRecomputeResponseDto(
                simulation_id = "sim_${recomputeRequests.size}",
                tenant_id = request.tenant_id,
                pack_id = request.pack_id,
                scenario_type = request.scenario_type,
                horizon_days = request.horizon_days,
                monte_carlo = MonteCarloBandsDto(
                    p10 = 4200.0,
                    p50 = 9800.0,
                    p90 = 15400.0,
                    mean = 9900.0,
                    std_dev = 2100.0,
                    prob_positive_pct = 92.0,
                    iterations = request.iterations,
                    seed = request.seed
                ),
                violated_rules = violations,
                is_compliant = violations.isEmpty(),
                elapsed_ms = 11.4,
                llm_calls = 0,
                provenance = SimulationProvenanceDto(
                    baseline_source = "erp_historical",
                    active_rules_count = 3,
                    yaml_rules_count = 2,
                    memory_rules_count = 1,
                    cited_documents = listOf("politica_comercial.pdf")
                )
            )
        }

        override suspend fun listMemoryRules(packId: String, tenantId: String, status: String?): MemoryRuleListResponseDto =
            MemoryRuleListResponseDto(tenant_id = tenantId, pack_id = packId, total = 0)

        override suspend fun getMemorySuggestions(packId: String, tenantId: String, windowDays: Int, minHits: Int): MemoryGovernanceFeedResponseDto {
            return MemoryGovernanceFeedResponseDto(
                tenant_id = tenantId,
                pack_id = packId,
                candidate_rules = listOf(
                    BusinessRuleDto(
                        rule_id = "r_cand_1",
                        tenant_id = tenantId,
                        pack_id = packId,
                        rule_key = "margem_minima_curva_a",
                        metric = "gross_margin_pct",
                        operator = ">=",
                        threshold_value = 18.0,
                        severity = "HIGH",
                        status = "candidate",
                        origin = "profiler",
                        description = "Proteger margem mínima Curva A"
                    ),
                    BusinessRuleDto(
                        rule_id = "r_cand_2",
                        tenant_id = tenantId,
                        pack_id = packId,
                        rule_key = "desconto_max_b2b",
                        metric = "discount_pct",
                        operator = "<=",
                        threshold_value = 10.0,
                        severity = "MEDIUM",
                        status = "candidate",
                        origin = "profiler",
                        description = "Limitar desconto promocional"
                    )
                ),
                suggested_simulations = listOf(
                    SuggestedSimulationCardDto(
                        card_id = "sug_1",
                        tenant_id = tenantId,
                        pack_id = packId,
                        topic_key = "reajuste_curva_a",
                        entity_type = "category",
                        metric_key = "gross_margin_pct",
                        hit_count = 5,
                        recommended_scenario = "margin_protection",
                        suggested_shocks = ShockVectorDto(price_delta_pct = 4.0, discount_pct = 2.0),
                        title = "Proteção de Margem Curva A",
                        reason = "5 consultas recorrentes na semana."
                    )
                ),
                pending_count = 2,
                llm_calls = 0
            )
        }

        override suspend fun decideMemoryRule(ruleId: String, request: RuleDecisionRequestDto): RuleDecisionResponseDto {
            ruleDecisions.add(ruleId to request)
            val newStatus = if (request.decision == "approve") "active" else "rejected"
            return RuleDecisionResponseDto(
                rule_id = ruleId,
                tenant_id = request.tenant_id,
                pack_id = request.pack_id,
                previous_status = "candidate",
                new_status = newStatus,
                decided_by = request.decided_by,
                decided_at = "2026-11-27T08:40:00Z",
                rule = BusinessRuleDto(
                    rule_id = ruleId,
                    tenant_id = request.tenant_id,
                    pack_id = request.pack_id,
                    rule_key = ruleId,
                    metric = "gross_margin_pct",
                    operator = ">=",
                    threshold_value = 18.0,
                    status = newStatus
                )
            )
        }

        override suspend fun runBacktest(request: BacktestRunRequestDto): BacktestRunResponseDto =
            BacktestRunResponseDto(tenant_id = request.tenant_id, pack_id = request.pack_id, evaluated_count = 0)

        override suspend fun getBacktestScorecard(packId: String, tenantId: String, limit: Int): RealizedRoiScorecardResponseDto {
            return RealizedRoiScorecardResponseDto(
                tenant_id = tenantId,
                pack_id = packId,
                period_days = 90,
                projected_brl = 30000.0,
                realized_brl = 33400.0,
                total_realized_brl = 33400.0,
                hit_rate_pct = 85.0,
                mean_abs_error_pct = 8.2,
                roi_multiple = 3.8,
                audited_actions_count = 4,
                items = listOf(
                    BacktestItemResultDto(
                        simulation_id = "bt_30",
                        scenario_type = "price_elasticity",
                        horizon_days = 30,
                        predicted_p10_brl = 9000.0,
                        predicted_p50_brl = 12000.0,
                        predicted_p90_brl = 15000.0,
                        realized_brl = 12800.0,
                        error_brl = 800.0,
                        error_pct = 6.7,
                        within_p10_p90 = true
                    ),
                    BacktestItemResultDto(
                        simulation_id = "bt_90",
                        scenario_type = "margin_protection",
                        horizon_days = 90,
                        predicted_p10_brl = 16000.0,
                        predicted_p50_brl = 18000.0,
                        predicted_p90_brl = 20000.0,
                        realized_brl = 20600.0,
                        error_brl = 2600.0,
                        error_pct = 14.4,
                        within_p10_p90 = false
                    )
                ),
                pending_calibration = CalibrationProposalDto(
                    rule_id = "calib_rule_1",
                    tenant_id = tenantId,
                    pack_id = packId,
                    current_factor = 1.0,
                    suggested_factor = 1.12,
                    mean_bias_pct = 11.3,
                    sample_size = 4,
                    reason = "Subestimativa sistemática de 11.3% no retorno."
                ),
                llm_calls = 0
            )
        }
    }

    private fun createSut(
        api: RecordingFakeApiService = RecordingFakeApiService(),
        initialPack: String = AuraDomainAdapter.PACK_RETAIL
    ): Pair<AuraIntelligenceViewModel, RecordingFakeApiService> {
        val holder = DomainPackStateHolder().apply { seedPackId(initialPack) }
        val repo = AuraIntelligenceRepository(
            apiService = api,
            domainPackStateHolder = holder,
            tenantIdProvider = { "tenant_test" }
        )
        val vm = AuraIntelligenceViewModel(
            repository = repo,
            injectedScope = testScope,
            ioDispatcher = Dispatchers.Default,
            debounceMs = 40L,
            autoLoadOnInit = false
        )
        return vm to api
    }

    @Test
    fun `slider drag debounces recompute calls and executes zero LLM calls`() = runBlocking {
        val (vm, api) = createSut()

        vm.onShocksChanged(ShockVectorDto(price_delta_pct = 1.0, discount_pct = 5.0))
        delay(10)
        vm.onShocksChanged(ShockVectorDto(price_delta_pct = 2.0, discount_pct = 8.0))
        delay(10)
        vm.onShocksChanged(ShockVectorDto(price_delta_pct = 3.0, discount_pct = 12.5))

        awaitUntil { api.recomputeRequests.isNotEmpty() && !vm.whatIfState.value.isLoading }

        assertEquals(1, api.recomputeRequests.size)
        val sent = api.recomputeRequests.single()
        assertEquals(3.0, sent.shocks.price_delta_pct, 0.001)
        assertEquals(12.5, sent.shocks.discount_pct, 0.001)
        assertEquals(AuraDomainAdapter.PACK_RETAIL, sent.pack_id)

        val ui = vm.whatIfState.value
        assertFalse(ui.isLoading)
        assertNotNull(ui.response)
        assertEquals(0, ui.response?.llm_calls)
        assertTrue(ui.hasViolations)
        assertEquals("teto_desconto", ui.response?.violated_rules?.firstOrNull()?.rule_key)
    }

    @Test
    fun `HiC candidate rule approval and rejection update immediate state`() = runBlocking {
        val (vm, api) = createSut()

        vm.refreshGovernance()
        awaitUntil { vm.governanceState.value.candidateRules.size == 2 && !vm.governanceState.value.isLoading }

        assertEquals(2, vm.governanceState.value.candidateRules.size)
        assertEquals(1, vm.governanceState.value.suggestedSimulations.size)

        vm.decideCandidateRule("r_cand_1", approve = true)
        vm.decideCandidateRule("r_cand_2", approve = false)
        awaitUntil {
            vm.governanceState.value.resolvedDecisions.size == 2 &&
                vm.governanceState.value.pendingRuleDecisions.isEmpty()
        }

        assertEquals(2, api.ruleDecisions.size)
        val decisionsByRule = api.ruleDecisions.associate { it.first to it.second.decision }
        assertEquals("approve", decisionsByRule["r_cand_1"])
        assertEquals("reject", decisionsByRule["r_cand_2"])
        assertEquals("approved", vm.governanceState.value.resolvedDecisions["r_cand_1"])
        assertEquals("rejected", vm.governanceState.value.resolvedDecisions["r_cand_2"])
        assertEquals(1, vm.governanceState.value.totalPendingCount)
    }

    @Test
    fun `applying proactive suggestion hydrates WhatIf simulator immediately with zero LLM calls`() = runBlocking {
        val (vm, api) = createSut()

        vm.refreshGovernance()
        awaitUntil { vm.governanceState.value.suggestedSimulations.isNotEmpty() && !vm.governanceState.value.isLoading }
        val suggestion = vm.governanceState.value.suggestedSimulations.first()

        vm.applySuggestedSimulation(suggestion)
        awaitUntil { api.recomputeRequests.isNotEmpty() && !vm.whatIfState.value.isLoading }

        assertEquals(1, api.recomputeRequests.size)
        assertEquals("margin_protection", vm.whatIfState.value.scenarioType)
        assertEquals(4.0, vm.whatIfState.value.shocks.price_delta_pct, 0.001)
        assertEquals(0, vm.whatIfState.value.response?.llm_calls)
        assertTrue(vm.buildAuditPrompt().contains("Proteção de Margem"))
    }

    @Test
    fun `backtesting scorecard filters horizons and decides calibration via HiC`() = runBlocking {
        val (vm, api) = createSut(initialPack = AuraDomainAdapter.PACK_PHARMACY)

        vm.refreshScorecard()
        awaitUntil { vm.scorecardState.value.scorecard != null && !vm.scorecardState.value.isLoading }

        assertEquals(2, vm.scorecardState.value.filteredItems.size)
        vm.selectScorecardHorizon(30)
        assertEquals(1, vm.scorecardState.value.filteredItems.size)
        assertEquals("bt_30", vm.scorecardState.value.filteredItems.first().simulation_id)

        vm.decideCalibration(approve = true)
        awaitUntil { vm.scorecardState.value.calibrationResolution != null }

        assertEquals("calib_rule_1", api.ruleDecisions.single().first)
        assertEquals("approve", api.ruleDecisions.single().second.decision)
        assertEquals("approved", vm.scorecardState.value.calibrationResolution)
    }

    @Test
    fun `TankTile is strictly isolated to fuel_convenience pack`() {
        assertTrue(isTankTileAllowedForPack(AuraDomainAdapter.PACK_FUEL))
        assertTrue(isTankTileAllowedForPack("postos_redes"))
        assertFalse(isTankTileAllowedForPack(AuraDomainAdapter.PACK_PHARMACY))
        assertFalse(isTankTileAllowedForPack(AuraDomainAdapter.PACK_RETAIL))
        assertFalse(isTankTileAllowedForPack(AuraDomainAdapter.PACK_AUTOCENTER))
        assertFalse(isTankTileAllowedForPack(AuraDomainAdapter.PACK_WHOLESALE))
    }
}
