package com.example.aurapostoassitance.di

import com.example.aurapostoassitance.data.local.ServerConfig
import com.example.aurapostoassitance.data.remote.AuraApiService
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    private const val DEFAULT_BASE_URL = "http://127.0.0.1:8000/"
    private const val TAILSCALE_HOST = "100.77.164.17"
    private const val OFFICE_LAN_HOST = "192.168.11.247"
    private const val DEFAULT_PORT = 8000

    @Provides
    @Singleton
    fun provideJson(): Json {
        return Json {
            ignoreUnknownKeys = true
            isLenient = true
        }
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(serverConfig: ServerConfig): OkHttpClient {
        return OkHttpClient.Builder()
            .connectTimeout(6, TimeUnit.SECONDS)
            .readTimeout(45, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .addInterceptor { chain ->
                val originalRequest = chain.request()
                val targetBaseUrl = serverConfig.getBaseUrl().toHttpUrlOrNull()

                fun buildRequestFor(scheme: String, host: String, port: Int) =
                    originalRequest.newBuilder()
                        .url(
                            originalRequest.url.newBuilder()
                                .scheme(scheme)
                                .host(host)
                                .port(port)
                                .build()
                        )
                        .header("Connection", "close")
                        .header("X-Partner-Key", "aura-partner-default-key")
                        .header("X-Aura-Key", "aura-partner-default-key")
                        .build()

                val primaryScheme = targetBaseUrl?.scheme ?: "http"
                val primaryHost = targetBaseUrl?.host ?: OFFICE_LAN_HOST
                val primaryPort = targetBaseUrl?.port ?: DEFAULT_PORT
                val primaryRequest = buildRequestFor(primaryScheme, primaryHost, primaryPort)

                try {
                    chain.proceed(primaryRequest)
                } catch (primaryError: java.io.IOException) {
                    val fallbackHost = when (primaryHost) {
                        OFFICE_LAN_HOST -> TAILSCALE_HOST
                        TAILSCALE_HOST -> OFFICE_LAN_HOST
                        else -> TAILSCALE_HOST
                    }
                    try {
                        val fallbackRequest = buildRequestFor("http", fallbackHost, DEFAULT_PORT)
                        val response = chain.proceed(fallbackRequest)
                        serverConfig.serverIp = "$fallbackHost:$DEFAULT_PORT"
                        response
                    } catch (_: java.io.IOException) {
                        throw primaryError
                    }
                }
            }
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient, json: Json): Retrofit {
        return Retrofit.Builder()
            .baseUrl(DEFAULT_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
    }
    
    @Provides
    @Singleton
    fun provideAuraApiService(retrofit: Retrofit): AuraApiService {
        return retrofit.create(AuraApiService::class.java)
    }
}
