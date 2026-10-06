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
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .addInterceptor { chain ->
                val originalRequest = chain.request()
                val targetBaseUrl = serverConfig.getBaseUrl().toHttpUrlOrNull()
                
                val newRequest = if (targetBaseUrl != null) {
                    val newUrl = originalRequest.url.newBuilder()
                        .scheme(targetBaseUrl.scheme)
                        .host(targetBaseUrl.host)
                        .port(targetBaseUrl.port)
                        .build()
                    originalRequest.newBuilder()
                        .url(newUrl)
                        .header("Connection", "close")
                        .build()
                } else {
                    originalRequest.newBuilder()
                        .header("Connection", "close")
                        .build()
                }
                chain.proceed(newRequest)
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
