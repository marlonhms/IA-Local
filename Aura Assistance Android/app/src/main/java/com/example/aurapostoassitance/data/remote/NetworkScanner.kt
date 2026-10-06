package com.example.aurapostoassitance.data.remote

import android.content.Context
import android.net.wifi.WifiManager
import android.util.Log
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NetworkScanner @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val scanClient = OkHttpClient.Builder()
        .connectTimeout(800, TimeUnit.MILLISECONDS)
        .readTimeout(800, TimeUnit.MILLISECONDS)
        .build()

    suspend fun findAuraServer(): String? = withContext(Dispatchers.IO) {
        val subnet = getSubnetPrefix() ?: "192.168.1."
        Log.d("NetworkScanner", "Scanning subnet prefix: $subnet")

        val candidates = mutableListOf<String>()
        candidates.add("127.0.0.1")
        candidates.add("100.77.164.17")
        
        for (i in 1..254) {
            candidates.add("$subnet$i")
        }

        val chunks = candidates.chunked(30)
        for (chunk in chunks) {
            val deferreds = chunk.map { ip ->
                async {
                    if (probeHost(ip)) ip else null
                }
            }
            val results = deferreds.awaitAll()
            val foundIp = results.firstOrNull { it != null }
            if (foundIp != null) {
                return@withContext "$foundIp:8000"
            }
        }
        return@withContext null
    }

    private fun probeHost(ip: String): Boolean {
        return try {
            val url = "http://$ip:8000/api/v1/aura/health"
            val request = Request.Builder().url(url).build()
            val response = scanClient.newCall(request).execute()
            if (response.isSuccessful) {
                val body = response.body?.string() ?: ""
                body.contains("AURA") || body.contains("healthy")
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }

    private fun getSubnetPrefix(): String? {
        return try {
            val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            val ipInt = wifiManager?.connectionInfo?.ipAddress ?: 0
            if (ipInt == 0) return null
            String.format(
                "%d.%d.%d.",
                ipInt and 0xff,
                ipInt shr 8 and 0xff,
                ipInt shr 16 and 0xff
            )
        } catch (e: Exception) {
            null
        }
    }
}
