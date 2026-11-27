package com.example.aurapostoassitance.data.remote

import com.example.aurapostoassitance.data.local.DomainPackStateHolder
import com.example.aurapostoassitance.data.local.ServerConfig
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repositório para os endpoints determinísticos do Carbon Core:
 * - Simulação What-If (`/api/v1/simulate/recompute`)
 * - Memória Institucional HiC & Sugestões Proativas (`/api/v1/memory/...`)
 * - Backtesting Previsto vs. Realizado (`/api/v1/simulate/backtest/...`)
 *
 * Também sincroniza automaticamente qualquer `pack_id` retornado pelo backend no
 * `DomainPackStateHolder` (`StateFlow<String>`).
 */
@Singleton
class AuraIntelligenceRepository(
    private val apiService: AuraApiService,
    private val domainPackStateHolder: DomainPackStateHolder,
    private val tenantIdProvider: () -> String,
    private val onPackIdSynced: (String) -> Unit = {}
) {

    @Inject
    constructor(
        apiService: AuraApiService,
        serverConfig: ServerConfig,
        domainPackStateHolder: DomainPackStateHolder
    ) : this(
        apiService = apiService,
        domainPackStateHolder = domainPackStateHolder,
        tenantIdProvider = { serverConfig.tenantId },
        onPackIdSynced = { syncedPack ->
            if (serverConfig.activePackId != syncedPack) {
                serverConfig.activePackId = syncedPack
            }
        }
    )

    val activePackId: StateFlow<String> = domainPackStateHolder.activePackId

    suspend fun getZeroClickFeed(packId: String? = null): ZeroClickFeedResponse {
        val targetPack = packId ?: activePackId.value
        val response = apiService.getZeroClickFeed(packId = targetPack)
        syncPackId(response.pack_id)
        return response
    }

    suspend fun recomputeSimulation(
        scenarioType: String,
        shocks: ShockVectorDto = ShockVectorDto(),
        horizonDays: Int = 30,
        baseline: SimulationBaselineDto? = null,
        simulationId: String? = null,
        iterations: Int = 5000,
        seed: Int = 42,
        persistSnapshot: Boolean = false,
        createdBy: String = "operator",
        packId: String = activePackId.value,
        tenantId: String = tenantIdProvider()
    ): SimulationRecomputeResponseDto {
        val request = SimulationRecomputeRequestDto(
            tenant_id = tenantId,
            pack_id = packId,
            simulation_id = simulationId,
            scenario_type = scenarioType,
            horizon_days = horizonDays,
            baseline = baseline,
            shocks = shocks,
            iterations = iterations,
            seed = seed,
            persist_snapshot = persistSnapshot,
            created_by = createdBy
        )
        val response = apiService.recomputeSimulation(request)
        syncPackId(response.pack_id)
        return response
    }

    suspend fun listMemoryRules(
        status: String? = "candidate",
        packId: String = activePackId.value,
        tenantId: String = tenantIdProvider()
    ): MemoryRuleListResponseDto {
        val response = apiService.listMemoryRules(
            packId = packId,
            tenantId = tenantId,
            status = status
        )
        syncPackId(response.pack_id)
        return response
    }

    suspend fun getMemorySuggestions(
        windowDays: Int = 7,
        minHits: Int = 3,
        packId: String = activePackId.value,
        tenantId: String = tenantIdProvider()
    ): MemoryGovernanceFeedResponseDto {
        val response = apiService.getMemorySuggestions(
            packId = packId,
            tenantId = tenantId,
            windowDays = windowDays,
            minHits = minHits
        )
        syncPackId(response.pack_id)
        return response
    }

    suspend fun decideMemoryRule(
        ruleId: String,
        decision: String,
        reason: String = "",
        decidedBy: String = "operator",
        packId: String = activePackId.value,
        tenantId: String = tenantIdProvider()
    ): RuleDecisionResponseDto {
        val response = apiService.decideMemoryRule(
            ruleId = ruleId,
            request = RuleDecisionRequestDto(
                tenant_id = tenantId,
                pack_id = packId,
                decision = decision,
                decided_by = decidedBy,
                reason = reason
            )
        )
        syncPackId(response.pack_id)
        return response
    }

    suspend fun runBacktest(
        asOf: String? = null,
        limit: Int = 50,
        dryRun: Boolean = false,
        packId: String = activePackId.value,
        tenantId: String = tenantIdProvider()
    ): BacktestRunResponseDto {
        val response = apiService.runBacktest(
            BacktestRunRequestDto(
                tenant_id = tenantId,
                pack_id = packId,
                as_of = asOf,
                limit = limit,
                dry_run = dryRun
            )
        )
        syncPackId(response.pack_id)
        return response
    }

    suspend fun getBacktestScorecard(
        limit: Int = 20,
        packId: String = activePackId.value,
        tenantId: String = tenantIdProvider()
    ): RealizedRoiScorecardResponseDto {
        val response = apiService.getBacktestScorecard(
            packId = packId,
            tenantId = tenantId,
            limit = limit
        )
        syncPackId(response.pack_id)
        return response
    }

    private fun syncPackId(returnedPackId: String?) {
        if (returnedPackId.isNullOrBlank()) return
        val normalized = domainPackStateHolder.updatePackId(returnedPackId)
        onPackIdSynced(normalized)
    }
}
