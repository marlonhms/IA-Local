package com.example.aurapostoassitance.data.local

import android.content.Context
import com.example.aurapostoassitance.data.security.AuraKeystoreVault
import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

@Serializable
data class HandoffContact(
    val role: String,
    val name: String = "",
    val phone: String = ""
)

@Singleton
class ServerConfig @Inject constructor(
    @ApplicationContext context: Context,
    private val keystoreVault: AuraKeystoreVault
) {
    private val prefs = context.getSharedPreferences("aura_config", Context.MODE_PRIVATE)
    private val json = Json { ignoreUnknownKeys = true }

    var serverIp: String
        get() = prefs.getString("server_ip", "192.168.11.247:8000") ?: "192.168.11.247:8000"
        set(value) {
            prefs.edit().putString("server_ip", value.trim()).apply()
        }

    var hasConnected: Boolean
        get() = prefs.getBoolean("has_connected", prefs.contains("server_ip"))
        set(value) {
            prefs.edit().putBoolean("has_connected", value).apply()
        }

    var lastHandoffRole: String
        get() = prefs.getString("handoff_last_role", "Contador") ?: "Contador"
        set(value) {
            prefs.edit().putString("handoff_last_role", value).apply()
        }

    var activePackId: String
        get() = AuraDomainAdapter.normalizePackId(
            prefs.getString("active_pack_id", AuraDomainAdapter.PACK_FUEL)
        )
        set(value) {
            prefs.edit().putString("active_pack_id", AuraDomainAdapter.normalizePackId(value)).apply()
        }

    /** Chave de API armazenada de forma criptografada no Android Keystore (AES-256-GCM). */
    var apiKey: String
        get() = keystoreVault.apiKey.orEmpty()
        set(value) {
            keystoreVault.apiKey = value.trim().ifBlank { null }
            // Limpa eventual legado em texto claro
            if (prefs.contains("aura_api_key")) {
                prefs.edit().remove("aura_api_key").apply()
            }
        }

    /** Chave dedicada de Parceiro (AURA_PARTNER_API_KEY) para rotas partner (Carbon Core P0.1). */
    var partnerApiKey: String
        get() = keystoreVault.partnerApiKey.orEmpty()
        set(value) {
            keystoreVault.partnerApiKey = value.trim().ifBlank { null }
        }

    var tenantId: String
        get() = keystoreVault.tenantId
        set(value) {
            keystoreVault.tenantId = value
        }

    var filialId: String
        get() = keystoreVault.filialId
        set(value) {
            keystoreVault.filialId = value
        }

    fun getHandoffContacts(): List<HandoffContact> {
        val defaults = listOf("Contador", "Gerente de Pista", "Fornecedor", "Outro")
        val raw = prefs.getString("handoff_contacts_json", null)
        val saved = if (!raw.isNullOrBlank()) {
            runCatching { json.decodeFromString<List<HandoffContact>>(raw) }.getOrDefault(emptyList())
        } else {
            emptyList()
        }
        val byRole = saved.associateBy { it.role }
        val merged = defaults.map { role -> byRole[role] ?: HandoffContact(role = role) }
        val extras = saved.filter { contact -> defaults.none { it.equals(contact.role, ignoreCase = true) } }
        return merged + extras
    }

    fun saveHandoffContact(contact: HandoffContact) {
        val current = getHandoffContacts().toMutableList()
        val idx = current.indexOfFirst { it.role.equals(contact.role, ignoreCase = true) }
        val sanitized = contact.copy(
            role = contact.role.trim().ifBlank { "Outro" },
            name = contact.name.trim(),
            phone = contact.phone.filter { it.isDigit() }
        )
        if (idx >= 0) {
            current[idx] = sanitized
        } else {
            current.add(sanitized)
        }
        prefs.edit()
            .putString("handoff_contacts_json", json.encodeToString(current))
            .putString("handoff_last_role", sanitized.role)
            .apply()
    }

    fun getBaseUrl(): String {
        var cleanIp = serverIp.trim()
        if (!cleanIp.startsWith("http://") && !cleanIp.startsWith("https://")) {
            cleanIp = "http://$cleanIp"
        }
        if (!cleanIp.endsWith("/")) {
            cleanIp = "$cleanIp/"
        }
        return cleanIp
    }
}
