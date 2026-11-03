package com.example.aurapostoassitance.ui.entrance

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aurapostoassitance.data.local.ServerConfig
import com.example.aurapostoassitance.data.remote.AuraApiService
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import javax.inject.Inject

sealed interface EntranceStep {
    data object Awakening : EntranceStep
    data class Connecting(val route: String) : EntranceStep
    data class Success(val route: String) : EntranceStep
    data class OfflineFallback(val route: String) : EntranceStep
    data object NeedsSetup : EntranceStep
}

@HiltViewModel
class AuraEntranceViewModel @Inject constructor(
    private val serverConfig: ServerConfig,
    private val apiService: AuraApiService
) : ViewModel() {

    private val _step = MutableStateFlow<EntranceStep>(EntranceStep.Awakening)
    val step: StateFlow<EntranceStep> = _step.asStateFlow()

    fun startEntranceSequence(
        onNavigateToDashboard: () -> Unit,
        onNavigateToSetup: () -> Unit
    ) {
        viewModelScope.launch {
            // Fase 1: Despertar da AURA (Emergência com efeito WOW de giroscópio)
            _step.value = EntranceStep.Awakening
            delay(1400)

            val rememberedRoute = serverConfig.serverIp
            val hasPreviousConnection = serverConfig.hasConnected

            if (hasPreviousConnection) {
                // Lembra a última rota e tenta conectar em segundo plano
                _step.value = EntranceStep.Connecting(rememberedRoute)

                val healthCheck = withTimeoutOrNull(2500) {
                    try {
                        val response = apiService.checkHealth()
                        response.status == "healthy" || response.status.isNotEmpty()
                    } catch (e: Exception) {
                        false
                    }
                } ?: false

                if (healthCheck) {
                    _step.value = EntranceStep.Success(rememberedRoute)
                    delay(700)
                    onNavigateToDashboard()
                } else {
                    // Servidor ocupado ou offline: transiciona fluidamente para o dashboard com persistência local
                    _step.value = EntranceStep.OfflineFallback(rememberedRoute)
                    delay(800)
                    onNavigateToDashboard()
                }
            } else {
                // Primeira vez abrindo o app: orienta para o Setup de conexão
                _step.value = EntranceStep.NeedsSetup
                delay(800)
                onNavigateToSetup()
            }
        }
    }
}
