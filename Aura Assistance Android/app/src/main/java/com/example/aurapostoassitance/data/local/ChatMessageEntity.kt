package com.example.aurapostoassitance.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "chat_messages")
data class ChatMessageEntity(
    @PrimaryKey val id: String,
    val sessionId: String = "default",
    val text: String,
    val isFromUser: Boolean,
    val timestamp: Long = System.currentTimeMillis(),
    /** Envelope GenUI (JSON) associado a mensagem da AURA, quando houver card estruturado. */
    val envelopeJson: String? = null,
    /** Trilha cronológica das etapas e ferramentas consultadas pela IA (JSON Array). */
    val reasoningJson: String? = null
)
