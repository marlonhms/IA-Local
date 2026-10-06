package com.example.aurapostoassitance.data.local

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ServerConfig @Inject constructor(
    @ApplicationContext context: Context
) {
    private val prefs = context.getSharedPreferences("aura_config", Context.MODE_PRIVATE)

    var serverIp: String
        get() = prefs.getString("server_ip", "127.0.0.1:8000") ?: "127.0.0.1:8000"
        set(value) {
            prefs.edit().putString("server_ip", value.trim()).apply()
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
