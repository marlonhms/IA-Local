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
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import javax.inject.Inject

data class QrPairingResult(
    val host: String,
    val apiKey: String?,
    val packId: String?
)

@HiltViewModel
class SetupViewModel @Inject constructor(
    private val apiService: AuraApiService,
    private val serverConfig: ServerConfig,
    private val networkScanner: NetworkScanner,
    private val json: Json
) : ViewModel() {

    private val _isScanning = MutableStateFlow(false)
    val isScanning: StateFlow<Boolean> = _isScanning.asStateFlow()

    fun getInitialIp(): String = serverConfig.serverIp

    fun getInitialApiKey(): String = serverConfig.apiKey

    fun getInitialPartnerApiKey(): String = serverConfig.partnerApiKey

    fun saveApiKey(key: String) {
        serverConfig.apiKey = key.trim()
    }

    fun savePartnerApiKey(key: String) {
        serverConfig.partnerApiKey = key.trim()
    }

    /**
     * Interpreta payload JSON de pareamento QR Code gerado pelo painel web AURA:
     * {"host":"100.77.164.17:8000","api_key":"...","tenant_id":"...","filial_id":"...","pack_id":"..."}
     */
    fun parseQrPairingPayload(raw: String): QrPairingResult? = runCatching {
        val obj = json.parseToJsonElement(raw.trim()).jsonObject
        val host = obj["host"]?.jsonPrimitive?.contentOrNull
            ?: obj["server_ip"]?.jsonPrimitive?.contentOrNull
            ?: return null
        val key = obj["api_key"]?.jsonPrimitive?.contentOrNull
        val partnerKey = obj["partner_api_key"]?.jsonPrimitive?.contentOrNull
        val tenant = obj["tenant_id"]?.jsonPrimitive?.contentOrNull
        val filial = obj["filial_id"]?.jsonPrimitive?.contentOrNull
        val pack = obj["pack_id"]?.jsonPrimitive?.contentOrNull

        serverConfig.serverIp = host
        if (!key.isNullOrBlank()) serverConfig.apiKey = key
        if (!partnerKey.isNullOrBlank()) serverConfig.partnerApiKey = partnerKey
        if (!tenant.isNullOrBlank()) serverConfig.tenantId = tenant
        if (!filial.isNullOrBlank()) serverConfig.filialId = filial
        if (!pack.isNullOrBlank()) serverConfig.activePackId = pack

        QrPairingResult(host = host, apiKey = key, packId = pack)
    }.getOrNull()

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

    fun testConnection(
        ipAddress: String,
        apiKey: String = serverConfig.apiKey,
        partnerApiKey: String = serverConfig.partnerApiKey,
        onResult: (Boolean, String?) -> Unit
    ) {
        serverConfig.serverIp = ipAddress.trim()
        if (apiKey.isNotBlank()) {
            serverConfig.apiKey = apiKey.trim()
        }
        if (partnerApiKey.isNotBlank()) {
            serverConfig.partnerApiKey = partnerApiKey.trim()
        }
        viewModelScope.launch {
            try {
                val response = apiService.checkHealth()
                val success = response.status == "healthy" || response.status.isNotEmpty()
                if (success) {
                    serverConfig.hasConnected = true
                    onResult(true, null)
                } else {
                    onResult(false, "Servidor respondeu sem status saudável.")
                }
            } catch (e: retrofit2.HttpException) {
                if (e.code() == 401) {
                    onResult(false, "Chave X-API-Key inválida ou ausente (HTTP 401).")
                } else {
                    onResult(false, "Erro HTTP ${e.code()} ao conectar em $ipAddress.")
                }
            } catch (e: Exception) {
                onResult(false, "Falha ao conectar em $ipAddress. Verifique rede ou Tailscale.")
            }
        }
    }
}
