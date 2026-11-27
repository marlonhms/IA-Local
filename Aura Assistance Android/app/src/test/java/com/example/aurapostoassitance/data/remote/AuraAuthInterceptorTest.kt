package com.example.aurapostoassitance.data.remote

import okhttp3.Call
import okhttp3.Connection
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Protocol
import okhttp3.Request
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.util.concurrent.TimeUnit

class AuraAuthInterceptorTest {

    private class FakeCredentialsProvider(
        var key: String? = null,
        var partnerKey: String? = null
    ) : AuraAuthCredentialsProvider {
        val authExpiredReasons = mutableListOf<String>()

        override fun resolveApiKey(): String? = key
        override fun resolvePartnerApiKey(): String? = partnerKey
        override fun notifyAuthExpired(reason: String) {
            authExpiredReasons.add(reason)
        }
    }

    private class FakeEndpointProvider(
        var baseUrl: String = "http://100.77.164.17:8000/",
        var packId: String = "fuel_convenience"
    ) : AuraNetworkEndpointProvider {
        val updatedHosts = mutableListOf<String>()

        override fun resolveBaseUrl(): String = baseUrl
        override fun resolveActivePackId(): String = packId
        override fun updateServerHostPort(hostPort: String) {
            updatedHosts.add(hostPort)
        }
    }

    private class FakeChain(
        initialRequest: Request,
        private val responseCode: Int = 200
    ) : Interceptor.Chain {
        var proceededRequest: Request? = null
            private set
        private var currentRequest: Request = initialRequest

        override fun request(): Request = currentRequest

        override fun proceed(request: Request): Response {
            proceededRequest = request
            return Response.Builder()
                .request(request)
                .protocol(Protocol.HTTP_1_1)
                .code(responseCode)
                .message("OK")
                .body("{}".toResponseBody("application/json".toMediaType()))
                .build()
        }

        override fun connection(): Connection? = null
        override fun call(): Call = throw UnsupportedOperationException("Not needed")
        override fun connectTimeoutMillis(): Int = 6000
        override fun withConnectTimeout(timeout: Int, unit: TimeUnit): Interceptor.Chain = this
        override fun readTimeoutMillis(): Int = 45000
        override fun withReadTimeout(timeout: Int, unit: TimeUnit): Interceptor.Chain = this
        override fun writeTimeoutMillis(): Int = 15000
        override fun withWriteTimeout(timeout: Int, unit: TimeUnit): Interceptor.Chain = this
    }

    @Test
    fun `injects X-API-Key Bearer X-Partner-Key and X-Pack-Id over Tailscale URL for REST and SSE`() {
        val creds = FakeCredentialsProvider(key = "aura-secret-key-123", partnerKey = "partner-456")
        val endpoint = FakeEndpointProvider(
            baseUrl = "http://100.77.164.17:8443/",
            packId = "pharmacy_health"
        )
        val interceptor = AuraAuthInterceptor(endpoint, creds)

        val restChain = FakeChain(
            Request.Builder().url("http://127.0.0.1:8000/api/v1/simulate/recompute").build()
        )
        interceptor.intercept(restChain)

        val restReq = restChain.proceededRequest!!
        assertEquals("100.77.164.17", restReq.url.host)
        assertEquals(8443, restReq.url.port)
        assertEquals("/api/v1/simulate/recompute", restReq.url.encodedPath)
        assertEquals("aura-secret-key-123", restReq.header("X-API-Key"))
        assertEquals("Bearer aura-secret-key-123", restReq.header("Authorization"))
        assertEquals("partner-456", restReq.header("X-Partner-Key"))
        assertEquals("pharmacy_health", restReq.header("X-Pack-Id"))

        val sseChain = FakeChain(
            Request.Builder()
                .url("http://127.0.0.1:8000/api/v1/aura/chat")
                .addHeader("Accept", "text/event-stream")
                .build()
        )
        interceptor.intercept(sseChain)

        val sseReq = sseChain.proceededRequest!!
        assertEquals("aura-secret-key-123", sseReq.header("X-API-Key"))
        assertEquals("text/event-stream", sseReq.header("Accept"))
        assertEquals(0, creds.authExpiredReasons.size)
    }

    @Test
    fun `omits auth headers when api key is absent and notifies on HTTP 401`() {
        val creds = FakeCredentialsProvider(key = "   ", partnerKey = null)
        val endpoint = FakeEndpointProvider()
        val interceptor = AuraAuthInterceptor(endpoint, creds)

        val chain = FakeChain(
            Request.Builder().url("http://127.0.0.1:8000/api/v1/memory/rules").build(),
            responseCode = 401
        )
        val response = interceptor.intercept(chain)

        val sent = chain.proceededRequest!!
        assertNull(sent.header("X-API-Key"))
        assertNull(sent.header("Authorization"))
        assertNull(sent.header("X-Partner-Key"))
        assertEquals(401, response.code)
        assertEquals(1, creds.authExpiredReasons.size)
    }
}
