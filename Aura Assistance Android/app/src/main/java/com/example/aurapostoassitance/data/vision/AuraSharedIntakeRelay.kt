package com.example.aurapostoassitance.data.vision

import android.net.Uri
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

data class SharedDocumentPayload(
    val id: String,
    val localUri: Uri,
    val mimeType: String,
    val fileName: String
)

/**
 * Relay em memória para documentos (fotos, PDFs, XMLs NF-e) recebidos via
 * Share Intent do WhatsApp, e-mail ou gerenciador de arquivos.
 */
@Singleton
class AuraSharedIntakeRelay @Inject constructor() {
    private val _pendingDocument = MutableStateFlow<SharedDocumentPayload?>(null)
    val pendingDocument: StateFlow<SharedDocumentPayload?> = _pendingDocument.asStateFlow()

    private val _pendingTelemetry = MutableStateFlow<ScannedDocumentTelemetry?>(null)
    val pendingTelemetry: StateFlow<ScannedDocumentTelemetry?> = _pendingTelemetry.asStateFlow()

    fun publish(payload: SharedDocumentPayload) {
        _pendingDocument.value = payload
    }

    fun markConsumed(id: String) {
        if (_pendingDocument.value?.id == id) {
            _pendingDocument.value = null
        }
    }

    fun publishTelemetry(telemetry: ScannedDocumentTelemetry) {
        _pendingTelemetry.value = telemetry
    }

    fun consumeTelemetry(): ScannedDocumentTelemetry? {
        val current = _pendingTelemetry.value
        if (current != null) _pendingTelemetry.value = null
        return current
    }
}
