package com.example.aurapostoassitance.di

import com.example.aurapostoassitance.data.local.ServerConfig
import com.example.aurapostoassitance.data.remote.AuraApiService
import com.example.aurapostoassitance.data.remote.AuraAuthInterceptor
import com.example.aurapostoassitance.data.security.AuraKeystoreVault
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.ConnectionPool
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

    @Provides
    @Singleton
    fun provideJson(): Json {
        return Json {
            ignoreUnknownKeys = true
            isLenient = true
            encodeDefaults = true
        }
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(
        serverConfig: ServerConfig,
        keystoreVault: AuraKeystoreVault
    ): OkHttpClient {
        return OkHttpClient.Builder()
            .connectionPool(ConnectionPool(5, 5, TimeUnit.MINUTES))
            .connectTimeout(6, TimeUnit.SECONDS)
            .readTimeout(45, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .addInterceptor(
                AuraAuthInterceptor(
                    endpointProvider = serverConfig,
                    credentialsProvider = keystoreVault
                )
            )
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
