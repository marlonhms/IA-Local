package com.example.aurapostoassitance.di

import com.example.aurapostoassitance.data.npu.LiteRtNpuRuntime
import com.example.aurapostoassitance.data.npu.NpuInferenceRuntime
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class NpuModule {

    @Binds
    @Singleton
    abstract fun bindNpuInferenceRuntime(impl: LiteRtNpuRuntime): NpuInferenceRuntime
}
