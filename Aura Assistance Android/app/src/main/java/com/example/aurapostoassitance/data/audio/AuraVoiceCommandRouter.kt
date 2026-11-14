package com.example.aurapostoassitance.data.audio

import java.text.Normalizer
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

enum class AuraDirectVoiceAction {
    EXECUTE_OPTION_1,
    PLAY_BRIEFING,
    STOP_AUDIO,
    OPEN_VISION_SCANNER,
    FALLBACK_CHAT_QUERY
}

data class VoiceCommandResult(
    val action: AuraDirectVoiceAction,
    val matchedPhrase: String,
    val confidence: Float,
    val chatQuery: String? = null
)

/**
 * Roteador de Comandos de Voz Hands-Free (Modo Carro e Operação Rápida).
 * Identifica em < 0.2ms comandos de voz diretos como "aprovar 1", "ouvir resumo", "parar" e "escanear nota".
 */
@Singleton
class AuraVoiceCommandRouter @Inject constructor() {

    private val option1Phrases = listOf(
        "aprovar 1", "opcao 1", "confirmar compra", "aprovar compra",
        "sim aprove", "aprovar opcao 1", "comprar agora", "confirmo a compra", "aprova"
    )

    private val playBriefingPhrases = listOf(
        "ouvir resumo", "briefing matinal", "ler resumo", "ler radar",
        "tocar briefing", "tocar resumo", "ouvir briefing", "tocar audio", "ouvir audio"
    )

    private val stopAudioPhrases = listOf(
        "parar", "silenciar", "chega", "pause", "pausar", "cala a boca", "stop", "pare",
        "encerrar", "encerrar conversa", "pode parar", "tchau", "tchau aura", "ate mais"
    )

    private val visionPhrases = listOf(
        "escanear", "abrir scanner", "ler nota", "foto do tanque", "escanear nota",
        "olhos da aura", "tirar foto", "ler documento", "escanear danfe"
    )

    fun routeSpokenText(rawTranscript: String): VoiceCommandResult {
        val normalized = normalize(rawTranscript)

        for (phrase in stopAudioPhrases) {
            if (normalized == phrase || normalized.startsWith("$phrase ") || normalized.endsWith(" $phrase")) {
                return VoiceCommandResult(
                    action = AuraDirectVoiceAction.STOP_AUDIO,
                    matchedPhrase = phrase,
                    confidence = 0.98f
                )
            }
        }

        for (phrase in option1Phrases) {
            if (normalized.contains(phrase)) {
                return VoiceCommandResult(
                    action = AuraDirectVoiceAction.EXECUTE_OPTION_1,
                    matchedPhrase = phrase,
                    confidence = 0.95f
                )
            }
        }

        for (phrase in playBriefingPhrases) {
            if (normalized.contains(phrase)) {
                return VoiceCommandResult(
                    action = AuraDirectVoiceAction.PLAY_BRIEFING,
                    matchedPhrase = phrase,
                    confidence = 0.95f
                )
            }
        }

        for (phrase in visionPhrases) {
            if (normalized.contains(phrase)) {
                return VoiceCommandResult(
                    action = AuraDirectVoiceAction.OPEN_VISION_SCANNER,
                    matchedPhrase = phrase,
                    confidence = 0.92f
                )
            }
        }

        return VoiceCommandResult(
            action = AuraDirectVoiceAction.FALLBACK_CHAT_QUERY,
            matchedPhrase = "",
            confidence = 0.80f,
            chatQuery = rawTranscript
        )
    }

    private fun normalize(text: String): String {
        val n = Normalizer.normalize(text.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        return n.replace(Regex("\\p{M}"), "").trim()
    }
}
