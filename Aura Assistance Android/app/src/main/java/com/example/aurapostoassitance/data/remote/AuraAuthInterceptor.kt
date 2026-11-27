package com.example.aurapostoassitance.data.remote

import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response
import java.io.IOException

/**
 * Provedor de credenciais descriptografadas sob demanda (em produção via AndroidKeyStore).
 */
interface AuraAuthCredentialsProvider {
    fun resolveApiKey(): String?
    fun resolvePartnerApiKey(): String?
    fun notifyAuthExpired(reason: String)
}

/**
 * Provedor dinâmico da URL base (Tailscale / LAN) e do Domain Pack ativo.
 */
interface AuraNetworkEndpointProvider {
    fun resolveBaseUrl(): String
    fun resolveActivePackId(): String
    fun updateServerHostPort(hostPort: String)
}

/**
 * Interceptor OkHttp compartilhado por REST (Retrofit) e SSE (okhttp-sse):
 * - Reescreve scheme/host/port para a URL configurada (Tailscale ou LAN).
 * - Injeta dinamicamente `X-API-Key`, `Authorization: Bearer ...`, `X-Partner-Key` e `X-Pack-Id`.
 * - Aplica fallback controlado LAN <-> Tailscale em falhas de IO.
 * - Notifica expiração/ausência de chave em respostas HTTP 401.
 */
class AuraAuthInterceptor(
    private val endpointProvider: AuraNetworkEndpointProvider,
    private val credentialsProvider: AuraAuthCredentialsProvider,
    private val officeLanHost: String = DEFAULT_OFFICE_LAN_HOST,
    private val tailscaleHost: String = DEFAULT_TAILSCALE_HOST,
    private val defaultPort: Int = DEFAULT_PORT
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val targetBaseUrl = endpointProvider.resolveBaseUrl().toHttpUrlOrNull()

        val apiKey = credentialsProvider.resolveApiKey()?.takeIf { it.isNotBlank() }
        val partnerKey = credentialsProvider.resolvePartnerApiKey()?.takeIf { it.isNotBlank() } ?: apiKey
        val activePackId = endpointProvider.resolveActivePackId().takeIf { it.isNotBlank() }

        fun buildRequestFor(scheme: String, host: String, port: Int): Request =
            originalRequest.newBuilder()
                .url(
                    originalRequest.url.newBuilder()
                        .scheme(scheme)
                        .host(host)
                        .port(port)
                        .build()
                )
                .apply {
                    if (apiKey != null) {
                        header("X-API-Key", apiKey)
                        header("Authorization", "Bearer $apiKey")
                    }
                    if (partnerKey != null) {
                        header("X-Partner-Key", partnerKey)
                    }
                    if (activePackId != null) {
                        header("X-Pack-Id", activePackId)
                    }
                }
                .build()

        val primaryScheme = targetBaseUrl?.scheme ?: "http"
        val primaryHost = targetBaseUrl?.host ?: officeLanHost
        val primaryPort = targetBaseUrl?.port ?: defaultPort
        val primaryRequest = buildRequestFor(primaryScheme, primaryHost, primaryPort)

        val response = try {
            chain.proceed(primaryRequest)
        } catch (primaryError: IOException) {
            val fallbackHost = when (primaryHost) {
                officeLanHost -> tailscaleHost
                tailscaleHost -> officeLanHost
                else -> tailscaleHost
            }
            try {
                val fallbackRequest = buildRequestFor("http", fallbackHost, defaultPort)
                val fallbackResponse = chain.proceed(fallbackRequest)
                endpointProvider.updateServerHostPort("$fallbackHost:$defaultPort")
                fallbackResponse
            } catch (_: IOException) {
                throw primaryError
            }
        }

        if (response.code == 401) {
            credentialsProvider.notifyAuthExpired(
                "Autenticação exigida pelo servidor AURA (HTTP 401). Configure a X-API-Key."
            )
        }
        return response
    }

    companion object {
        const val DEFAULT_TAILSCALE_HOST = "100.77.164.17"
        const val DEFAULT_OFFICE_LAN_HOST = "192.168.11.247"
        const val DEFAULT_PORT = 8000
    }
}
