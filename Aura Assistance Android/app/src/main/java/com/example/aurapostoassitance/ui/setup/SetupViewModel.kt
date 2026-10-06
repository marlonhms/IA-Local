package com.example.aurapostoassitance.ui.setup

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aurapostoassitance.data.local.ServerConfig
import com.example.aurapostoassitance.data.remote.AuraApiService
import com.example.aurapostoassitance.data.remote.NetworkScanner
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SetupViewModel @Inject constructor(
    private val apiService: AuraApiService,
    private val serverConfig: ServerConfig,
    private val networkScanner: NetworkScanner
) : ViewModel() {

    private val _isScanning = MutableStateFlow(false)
    val isScanning: StateFlow<Boolean> = _isScanning.asStateFlow()

    fun getInitialIp(): String {
        return serverConfig.serverIp
    }

    fun scanNetworkForServer(onFound: (String) -> Unit, onNotFound: () -> Unit) {
        _isScanning.value = true
        viewModelScope.launch {
            val foundIp = networkScanner.findAuraServer()
            _isScanning.value = false
            if (foundIp != null) {
                serverConfig.serverIp = foundIp
                onFound(foundIp)
            } else {
                onNotFound()
            }
        }
    }

    fun testConnection(ipAddress: String, onResult: (Boolean) -> Unit) {
        serverConfig.serverIp = ipAddress
        viewModelScope.launch {
            try {
                val response = apiService.checkHealth()
                onResult(response.status == "healthy" || response.status.isNotEmpty())
            } catch (e: Exception) {
                e.printStackTrace()
                onResult(false)
            }
        }
    }
}
