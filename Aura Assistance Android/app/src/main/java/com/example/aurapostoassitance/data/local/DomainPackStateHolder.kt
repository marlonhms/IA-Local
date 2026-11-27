package com.example.aurapostoassitance.data.local

import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Detentor reativo e testável do Domain Pack ativo (`pack_id`) compartilhado entre
 * camada de rede, repositórios e UI multi-vertical.
 */
@Singleton
class DomainPackStateHolder @Inject constructor() {

    private val _activePackId = MutableStateFlow(AuraDomainAdapter.PACK_FUEL)
    val activePackId: StateFlow<String> = _activePackId.asStateFlow()

    fun seedPackId(rawPackId: String?): String {
        val normalized = AuraDomainAdapter.normalizePackId(rawPackId)
        _activePackId.value = normalized
        return normalized
    }

    fun updatePackId(rawPackId: String?): String {
        if (rawPackId.isNullOrBlank()) return _activePackId.value
        val normalized = AuraDomainAdapter.normalizePackId(rawPackId)
        _activePackId.value = normalized
        return normalized
    }
}
