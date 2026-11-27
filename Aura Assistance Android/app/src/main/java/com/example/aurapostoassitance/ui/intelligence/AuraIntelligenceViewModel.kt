package com.example.aurapostoassitance.ui.intelligence

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aurapostoassitance.data.remote.AuraIntelligenceRepository
import com.example.aurapostoassitance.data.remote.ShockVectorDto
import com.example.aurapostoassitance.data.remote.SimulationBaselineDto
import com.example.aurapostoassitance.data.remote.SuggestedSimulationCardDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

private data class WhatIfRecomputeRequest(
    val packId: String,
    val scenarioType: String,
    val horizonDays: Int,
    val shocks: ShockVectorDto,
    val baseline: SimulationBaselineDto?,
    val immediate: Boolean
)

/**
 * ViewModel dedicado aos motores determinísticos da Fase 4B:
 * - Simulador What-If zero-token com debounce (~180ms)
 * - Governança HiC (regras candidatas e sugestões proativas do profiler)
 * - Scorecard de Backtesting (Previsto P10/P50/P90 vs. Realizado + calibração)
 */
@HiltViewModel
class AuraIntelligenceViewModel internal constructor(
    private val repository: AuraIntelligenceRepository,
    private val injectedScope: CoroutineScope?,
    private val ioDispatcher: CoroutineDispatcher,
    private val debounceMs: Long,
    private val autoLoadOnInit: Boolean
) : ViewModel() {

    @Inject
    constructor(repository: AuraIntelligenceRepository) : this(
        repository = repository,
        injectedScope = null,
        ioDispatcher = Dispatchers.IO,
        debounceMs = 180L,
        autoLoadOnInit = true
    )

    private val scope: CoroutineScope
        get() = injectedScope ?: viewModelScope

    val activePackId: StateFlow<String> = repository.activePackId

    private val _whatIfState = MutableStateFlow(
        WhatIfUiState(packId = repository.activePackId.value)
    )
    val whatIfState: StateFlow<WhatIfUiState> = _whatIfState.asStateFlow()

    private val _governanceState = MutableStateFlow(
        GovernanceHiCUiState(packId = repository.activePackId.value)
    )
    val governanceState: StateFlow<GovernanceHiCUiState> = _governanceState.asStateFlow()

    private val _scorecardState = MutableStateFlow(
        BacktestScorecardUiState(packId = repository.activePackId.value)
    )
    val scorecardState: StateFlow<BacktestScorecardUiState> = _scorecardState.asStateFlow()

    private val recomputeChannel = Channel<WhatIfRecomputeRequest>(Channel.CONFLATED)

    init {
        startRecomputePipeline()
        if (autoLoadOnInit) {
            observeActivePack()
        }
    }

    @OptIn(FlowPreview::class)
    private fun startRecomputePipeline() {
        scope.launch(ioDispatcher) {
            recomputeChannel
                .receiveAsFlow()
                .debounce { request -> if (request.immediate) 0L else debounceMs }
                .collectLatest { request ->
                    executeRecompute(request)
                }
        }
    }

    private fun observeActivePack() {
        scope.launch(ioDispatcher) {
            repository.activePackId
                .collect { packId ->
                    _whatIfState.update { it.copy(packId = packId) }
                    _governanceState.update {
                        it.copy(
                            packId = packId,
                            resolvedDecisions = emptyMap(),
                            errorMessage = null
                        )
                    }
                    _scorecardState.update {
                        it.copy(
                            packId = packId,
                            calibrationResolution = null,
                            errorMessage = null
                        )
                    }
                    refreshGovernance(packId)
                    refreshScorecard(packId)
                }
        }
    }

    fun onShocksChanged(shocks: ShockVectorDto) {
        _whatIfState.update { it.copy(shocks = shocks, errorMessage = null) }
        enqueueRecompute(immediate = false)
    }

    fun onHorizonChanged(horizonDays: Int) {
        if (_whatIfState.value.horizonDays == horizonDays) return
        _whatIfState.update { it.copy(horizonDays = horizonDays, errorMessage = null) }
        enqueueRecompute(immediate = true)
    }

    fun openScenario(
        scenarioType: String = "price_elasticity",
        title: String = "Simulador What-If",
        subtitle: String? = null,
        initialShocks: ShockVectorDto = ShockVectorDto(),
        horizonDays: Int = 30,
        baseline: SimulationBaselineDto? = null
    ) {
        _whatIfState.value = WhatIfUiState(
            packId = repository.activePackId.value,
            scenarioType = scenarioType,
            title = title,
            subtitle = subtitle,
            horizonDays = horizonDays,
            shocks = initialShocks,
            baseline = baseline,
            response = _whatIfState.value.response,
            isLoading = true,
            errorMessage = null
        )
        enqueueRecompute(immediate = true)
    }

    fun applySuggestedSimulation(card: SuggestedSimulationCardDto) {
        openScenario(
            scenarioType = card.recommended_scenario,
            title = card.title,
            subtitle = card.reason,
            initialShocks = card.suggested_shocks,
            horizonDays = _whatIfState.value.horizonDays,
            baseline = _whatIfState.value.baseline
        )
    }

    fun recomputeNow() {
        enqueueRecompute(immediate = true)
    }

    fun buildAuditPrompt(): String = AuraIntelligenceFormatters.buildWhatIfAuditPrompt(_whatIfState.value)

    private fun enqueueRecompute(immediate: Boolean) {
        val current = _whatIfState.value
        recomputeChannel.trySend(
            WhatIfRecomputeRequest(
                packId = current.packId,
                scenarioType = current.scenarioType,
                horizonDays = current.horizonDays,
                shocks = current.shocks,
                baseline = current.baseline,
                immediate = immediate
            )
        )
    }

    private suspend fun executeRecompute(request: WhatIfRecomputeRequest) {
        _whatIfState.update { it.copy(isLoading = true, errorMessage = null) }
        runCatching {
            repository.recomputeSimulation(
                scenarioType = request.scenarioType,
                shocks = request.shocks,
                horizonDays = request.horizonDays,
                baseline = request.baseline,
                persistSnapshot = false,
                packId = request.packId
            )
        }.onSuccess { result ->
            _whatIfState.update {
                it.copy(
                    packId = result.pack_id,
                    response = result,
                    isLoading = false,
                    errorMessage = null
                )
            }
        }.onFailure { err ->
            _whatIfState.update {
                it.copy(
                    isLoading = false,
                    errorMessage = err.localizedMessage ?: "Falha ao recalcular simulação."
                )
            }
        }
    }

    fun refreshGovernance(packId: String = repository.activePackId.value) {
        scope.launch(ioDispatcher) {
            _governanceState.update { it.copy(packId = packId, isLoading = true, errorMessage = null) }
            runCatching {
                repository.getMemorySuggestions(packId = packId)
            }.onSuccess { feed ->
                _governanceState.update {
                    it.copy(
                        packId = feed.pack_id,
                        candidateRules = feed.candidate_rules,
                        suggestedSimulations = feed.suggested_simulations,
                        isLoading = false,
                        errorMessage = null
                    )
                }
            }.onFailure { err ->
                _governanceState.update {
                    it.copy(
                        isLoading = false,
                        errorMessage = err.localizedMessage ?: "Não foi possível carregar pendências HiC."
                    )
                }
            }
        }
    }

    fun toggleGovernanceExpanded() {
        _governanceState.update { it.copy(isExpanded = !it.isExpanded) }
    }

    fun decideCandidateRule(ruleId: String, approve: Boolean, reason: String = "") {
        if (ruleId in _governanceState.value.pendingRuleDecisions) return
        val targetPackId = _governanceState.value.packId
        val decision = if (approve) "approve" else "reject"
        val resolution = if (approve) "approved" else "rejected"

        scope.launch(ioDispatcher) {
            _governanceState.update {
                it.copy(
                    pendingRuleDecisions = it.pendingRuleDecisions + ruleId,
                    errorMessage = null
                )
            }
            runCatching {
                repository.decideMemoryRule(
                    ruleId = ruleId,
                    decision = decision,
                    reason = reason,
                    packId = targetPackId
                )
            }.onSuccess { response ->
                _governanceState.update { current ->
                    current.copy(
                        pendingRuleDecisions = current.pendingRuleDecisions - ruleId,
                        resolvedDecisions = current.resolvedDecisions + (ruleId to resolution),
                        candidateRules = current.candidateRules.map { rule ->
                            if (rule.rule_id == ruleId) response.rule else rule
                        }
                    )
                }
            }.onFailure { err ->
                _governanceState.update { current ->
                    current.copy(
                        pendingRuleDecisions = current.pendingRuleDecisions - ruleId,
                        errorMessage = err.localizedMessage ?: "Falha ao registrar decisão HiC."
                    )
                }
            }
        }
    }

    fun refreshScorecard(packId: String = repository.activePackId.value) {
        scope.launch(ioDispatcher) {
            _scorecardState.update { it.copy(packId = packId, isLoading = true, errorMessage = null) }
            runCatching {
                repository.getBacktestScorecard(packId = packId)
            }.onSuccess { result ->
                _scorecardState.update {
                    it.copy(
                        packId = result.pack_id,
                        scorecard = result,
                        isLoading = false,
                        errorMessage = null
                    )
                }
            }.onFailure { err ->
                _scorecardState.update {
                    it.copy(
                        isLoading = false,
                        errorMessage = err.localizedMessage ?: "Não foi possível carregar o scorecard."
                    )
                }
            }
        }
    }

    fun selectScorecardHorizon(horizonDays: Int) {
        _scorecardState.update { it.copy(selectedHorizonDays = horizonDays) }
    }

    fun decideCalibration(approve: Boolean) {
        val currentState = _scorecardState.value
        val proposal = currentState.scorecard?.pending_calibration ?: return
        if (currentState.calibrationDecisionInFlight) return

        val decision = if (approve) "approve" else "reject"
        val resolution = if (approve) "approved" else "rejected"

        scope.launch(ioDispatcher) {
            _scorecardState.update {
                it.copy(calibrationDecisionInFlight = true, errorMessage = null)
            }
            runCatching {
                repository.decideMemoryRule(
                    ruleId = proposal.rule_id,
                    decision = decision,
                    reason = proposal.reason,
                    packId = proposal.pack_id
                )
            }.onSuccess {
                _scorecardState.update {
                    it.copy(
                        calibrationDecisionInFlight = false,
                        calibrationResolution = resolution
                    )
                }
            }.onFailure { err ->
                _scorecardState.update {
                    it.copy(
                        calibrationDecisionInFlight = false,
                        errorMessage = err.localizedMessage ?: "Falha ao decidir calibração."
                    )
                }
            }
        }
    }
}
