package com.example.aurapostoassitance.ui.dashboard

import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aurapostoassitance.data.audio.AuraVoiceManager
import com.example.aurapostoassitance.data.local.AuraOfflineVault
import com.example.aurapostoassitance.data.local.ServerConfig
import com.example.aurapostoassitance.data.local.memory.AuraSemanticMemoryVault
import com.example.aurapostoassitance.data.npu.AuraNpuEngine
import com.example.aurapostoassitance.data.npu.NpuHardwareStatus
import com.example.aurapostoassitance.data.remote.AuraApiService
import com.example.aurapostoassitance.data.remote.MorningBriefingRequest
import com.example.aurapostoassitance.data.remote.MorningBriefingResponse
import com.example.aurapostoassitance.data.remote.QuickActionRequest
import com.example.aurapostoassitance.data.security.AuraHardwareAuthManager
import com.example.aurapostoassitance.data.security.AuraKeystoreVault
import com.example.aurapostoassitance.data.sensors.AuraContextSensorManager
import com.example.aurapostoassitance.data.sensors.AuraPhysicalContext
import com.example.aurapostoassitance.data.vision.AuraSharedIntakeRelay
import com.example.aurapostoassitance.data.vision.AuraVisionNpuScanner
import com.example.aurapostoassitance.data.vision.ScannedDocumentTelemetry
import com.example.aurapostoassitance.ui.components.AuraIslandMetric
import com.example.aurapostoassitance.ui.components.AuraIslandTelemetry
import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import com.example.aurapostoassitance.ui.domain.DomainPackUiProfile
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SegmentChoice(
    val key: String,
    val label: String,
    val sublabel: String
)

sealed class BriefingUiState {
    object Idle : BriefingUiState()
    object Loading : BriefingUiState()
    data class Success(
        val briefing: MorningBriefingResponse,
        val isOfflineCached: Boolean = false
    ) : BriefingUiState()
    data class Error(val message: String) : BriefingUiState()
}

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val apiService: AuraApiService,
    private val voiceManager: AuraVoiceManager,
    private val npuEngine: AuraNpuEngine,
    private val offlineVault: AuraOfflineVault,
    private val serverConfig: ServerConfig,
    private val keystoreVault: AuraKeystoreVault,
    val hardwareAuthManager: AuraHardwareAuthManager,
    val visionScanner: AuraVisionNpuScanner,
    val memoryVault: AuraSemanticMemoryVault,
    val contextSensorManager: AuraContextSensorManager,
    private val sharedIntakeRelay: AuraSharedIntakeRelay
) : ViewModel() {

    fun submitVisionScan(telemetry: ScannedDocumentTelemetry) {
        sharedIntakeRelay.publishTelemetry(telemetry)
    }

    val availableProfiles: List<DomainPackUiProfile> = AuraDomainAdapter.allProfiles

    val availableSegments = availableProfiles.map {
        SegmentChoice(it.packId, it.shortLabel, it.subtitle)
    }

    val selectedSegment: StateFlow<String> = serverConfig.activePackIdFlow

    private val _isServerOnline = MutableStateFlow<Boolean?>(null)
    val isServerOnline: StateFlow<Boolean?> = _isServerOnline.asStateFlow()

    private val _authExpiredMessage = MutableStateFlow<String?>(null)
    val authExpiredMessage: StateFlow<String?> = _authExpiredMessage.asStateFlow()

    private val _islandTelemetry = MutableStateFlow(AuraIslandTelemetry())
    val islandTelemetry: StateFlow<AuraIslandTelemetry> = _islandTelemetry.asStateFlow()

    private val _briefingState = MutableStateFlow<BriefingUiState>(BriefingUiState.Loading)
    val briefingState: StateFlow<BriefingUiState> = _briefingState.asStateFlow()

    val hardwareStatus: StateFlow<NpuHardwareStatus> = npuEngine.hardwareStatus

    val isSpeaking: StateFlow<Boolean> = voiceManager.isSpeaking
    val speakingMessageId: StateFlow<String?> = voiceManager.speakingMessageId
    val voiceAmplitude: StateFlow<Float> = voiceManager.voiceAmplitude

    val physicalContext: StateFlow<AuraPhysicalContext> = contextSensorManager.contextState

    private val _actionFeedback = MutableStateFlow<String?>(null)
    val actionFeedback: StateFlow<String?> = _actionFeedback.asStateFlow()

    private val _signedActions = MutableStateFlow<Map<String, String>>(emptyMap())
    val signedActions: StateFlow<Map<String, String>> = _signedActions.asStateFlow()

    private val _isExecutingAction = MutableStateFlow(false)
    val isExecutingAction: StateFlow<Boolean> = _isExecutingAction.asStateFlow()

    private val _handoffUnreadCount = MutableStateFlow(0)
    val handoffUnreadCount: StateFlow<Int> = _handoffUnreadCount.asStateFlow()

    private val _handoffThreadCount = MutableStateFlow(0)
    val handoffThreadCount: StateFlow<Int> = _handoffThreadCount.asStateFlow()

    fun toggleCarMode() = contextSensorManager.toggleManualCarMode()

    fun dismissAuthExpired() {
        _authExpiredMessage.value = null
    }

    init {
        loadBriefing(selectedSegment.value)
        refreshLiveTelemetry(selectedSegment.value)
        startHandoffSummaryPolling()
        viewModelScope.launch {
            keystoreVault.authExpiredEvents.collect { msg ->
                _authExpiredMessage.value = msg
                _isServerOnline.value = false
            }
        }
    }

    fun refreshLiveTelemetry(packId: String = selectedSegment.value) {
        viewModelScope.launch {
            runCatching { apiService.checkHealth() }
                .onSuccess { _isServerOnline.value = true }
                .onFailure { _isServerOnline.value = false }

            runCatching { apiService.getZeroClickFeed(packId = packId) }
                .onSuccess { feed ->
                    val allItems = (feed.alerts + feed.metrics).map { m ->
                        AuraIslandMetric(
                            title = m.label,
                            value = m.value,
                            detail = m.detail ?: m.value,
                            status = m.status,
                            actionLabel = "Analisar",
                            actionQuery = m.action_query ?: "Detalhe o indicador ${m.label} (${m.value}) e recomende ações."
                        )
                    }
                    val summary = feed.headline?.takeIf { it.isNotBlank() }
                        ?: allItems.take(2).joinToString(" • ") { "${it.title}: ${it.value}" }
                            .ifBlank { "Telemetria ao vivo conectada • Toque para auditar" }
                    _islandTelemetry.value = AuraIslandTelemetry(
                        isLive = true,
                        summaryPill = summary,
                        items = allItems
                    )
                }
                .onFailure {
                    val profile = AuraDomainAdapter.profileFor(packId)
                    _islandTelemetry.value = AuraIslandTelemetry(
                        isLive = false,
                        summaryPill = "${profile.shortLabel} • Toque para diagnóstico ao vivo",
                        items = emptyList()
                    )
                }
        }
    }

    private fun startHandoffSummaryPolling() {
        viewModelScope.launch {
            while (true) {
                refreshHandoffSummary()
                delay(15000L)
            }
        }
    }

    fun refreshHandoffSummary() {
        viewModelScope.launch {
            runCatching {
                apiService.getHandoffThreads(syncEvolution = true, limit = 30)
            }.onSuccess { res ->
                _handoffUnreadCount.value = res.total_unread
                _handoffThreadCount.value = res.threads.size
            }
        }
    }

    fun selectSegment(segmentKey: String) {
        val normalized = AuraDomainAdapter.normalizePackId(segmentKey)
        if (selectedSegment.value == normalized) return
        serverConfig.activePackId = normalized
        stopBriefingAudio()
        loadBriefing(normalized)
        refreshLiveTelemetry(normalized)
    }

    fun loadBriefing(segmentKey: String = selectedSegment.value) {
        viewModelScope.launch {
            _actionFeedback.value = null
            val profile = AuraDomainAdapter.profileFor(segmentKey)

            // 1. Resposta instantânea em 0ms através do cofre offline (Offline Vault)
            val cached = offlineVault.getBriefing(profile.legacySegmentKey)
            _briefingState.value = BriefingUiState.Success(cached, isOfflineCached = true)

            // 2. Sincronização em segundo plano com a AURA Local
            try {
                val response = apiService.getMorningBriefing(
                    MorningBriefingRequest(
                        segment = profile.legacySegmentKey,
                        manager_name = "Marlon Henrique",
                        business_name = profile.displayName
                    )
                )
                offlineVault.saveBriefing(profile.legacySegmentKey, response)
                _isServerOnline.value = true
                _briefingState.value = BriefingUiState.Success(response, isOfflineCached = false)
            } catch (e: Exception) {
                // Mantém a visualização com o cofre offline ativo
                _briefingState.value = BriefingUiState.Success(cached, isOfflineCached = true)
            }
        }
    }

    fun togglePlayBriefing() {
        val state = _briefingState.value
        if (state !is BriefingUiState.Success) return

        val messageId = "briefing_${selectedSegment.value}"
        if (voiceManager.isSpeaking.value && voiceManager.speakingMessageId.value == messageId) {
            voiceManager.stopSpeaking()
        } else {
            voiceManager.speak(messageId, state.briefing.oralVoiceScript)
        }
    }

    fun stopBriefingAudio() {
        if (voiceManager.isSpeaking.value) {
            voiceManager.stopSpeaking()
        }
    }

    /**
     * Autentica com biometria no Qualcomm TEE (SM7435) antes de registrar e assinar a ordem executiva.
     */
    fun authenticateAndExecuteBriefingAction(
        activity: FragmentActivity,
        optionKey: String,
        description: String
    ) {
        val payload = "ACTION:BRIEFING|SEGMENT:${selectedSegment.value}|OPT:$optionKey|DESC:$description|TS:${System.currentTimeMillis()}"
        hardwareAuthManager.authenticateAndSignOrder(
            activity = activity,
            orderTitle = "Alçada Executiva • $description",
            orderSubtitle = "Assinatura Criptográfica Qualcomm TEE",
            orderDescription = "Confirme com a biometria para autorizar e assinar a ordem no silício do Snapdragon 7s Gen 2.",
            payloadToSign = payload,
            onSuccess = { signature, isHardware ->
                executeSignedBriefingAction(optionKey, description, signature, isHardware)
            },
            onError = { errorMsg ->
                _actionFeedback.value = errorMsg
            }
        )
    }

    fun executeBriefingAction(optionKey: String, description: String) {
        executeSignedBriefingAction(optionKey, description, null, false)
    }

    fun executeSignedBriefingAction(
        optionKey: String,
        description: String,
        signature: String?,
        isHardwareBacked: Boolean
    ) {
        viewModelScope.launch {
            _isExecutingAction.value = true
            val secBadge = if (isHardwareBacked) "🔐 TEE SM7435" else "🔑 Assinado"
            val localReceipt = "CMD-2026-${(System.currentTimeMillis() % 90000 + 10000)}"

            try {
                // 1. Edge-First: Registra imediatamente no Cofre Semântico Local do Silício
                memoryVault.indexMemory(
                    category = "DECISAO_EXECUTIVA",
                    title = description,
                    content = "Opção $optionKey ($description) assinada para ${selectedSegment.value}. Recibo: $localReceipt. TEE: $isHardwareBacked",
                    segment = selectedSegment.value
                )

                _signedActions.update { it + (optionKey to localReceipt) }
                _actionFeedback.value = "Ordem assinada no Qualcomm TEE! [$secBadge | Recibo: $localReceipt]"

                if (signature != null) {
                    voiceManager.speak("action_conf", "Ordem assinada no silício e registrada no Command Journal.")
                }

                // 2. Sincronização resiliente com o Backend (AURA Local :8000)
                val stationId = when (selectedSegment.value) {
                    "postos_redes", "POSTOS" -> "posto_01"
                    "varejo", "VAREJO" -> "varejo_01"
                    else -> "posto_01"
                }

                val req = QuickActionRequest(
                    action_type = "BRIEFING_QUICK_ACTION",
                    option_key = optionKey,
                    actor_name = "Marlon Henrique",
                    parameters = buildMap {
                        put("segment", selectedSegment.value)
                        put("description", description)
                        if (signature != null) {
                            put("tee_signature", signature)
                            put("hardware_backed", isHardwareBacked.toString())
                            put("security_level", hardwareAuthManager.getHardwareSecurityLevel())
                        }
                    }
                )

                val res = try {
                    apiService.executeStationQuickAction(stationId, req)
                } catch (_: Exception) {
                    try {
                        apiService.executeQuickAction(req)
                    } catch (_: Exception) {
                        null
                    }
                }

                if (res != null) {
                    val finalReceipt = res.journal_id ?: res.voucher_id ?: localReceipt
                    _signedActions.update { it + (optionKey to finalReceipt) }
                    _actionFeedback.value = "${res.confirmation_text ?: "Ação sincronizada com sucesso!"} [$secBadge | Recibo: $finalReceipt]"
                }
            } catch (e: Exception) {
                android.util.Log.w("DashboardViewModel", "Falha de sync no background (usando recibo local): ${e.message}")
            } finally {
                _isExecutingAction.value = false
            }
        }
    }

    fun clearFeedback() {
        _actionFeedback.value = null
    }
}
