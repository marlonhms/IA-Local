package com.example.aurapostoassitance.data.audio

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuraVoiceManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val mainHandler = Handler(Looper.getMainLooper())

    // --- StateFlows para UI reativa ---
    private val _isListening = MutableStateFlow(false)
    val isListening: StateFlow<Boolean> = _isListening.asStateFlow()

    private val _spokenText = MutableStateFlow("")
    val spokenText: StateFlow<String> = _spokenText.asStateFlow()

    private val _voiceRms = MutableStateFlow(0.1f)
    val voiceRms: StateFlow<Float> = _voiceRms.asStateFlow()

    private val _isSpeaking = MutableStateFlow(false)
    val isSpeaking: StateFlow<Boolean> = _isSpeaking.asStateFlow()

    private val _speakingMessageId = MutableStateFlow<String?>(null)
    val speakingMessageId: StateFlow<String?> = _speakingMessageId.asStateFlow()

    private var speechRecognizer: SpeechRecognizer? = null
    private var onSpeechResultCallback: ((String) -> Unit)? = null

    private var tts: TextToSpeech? = null
    private var isTtsInitialized = false

    init {
        initTts()
    }

    private fun initTts() {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale("pt", "BR")
                tts?.setPitch(1.0f)
                tts?.setSpeechRate(1.08f) // Cadência executiva dinâmica
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {
                        _isSpeaking.value = true
                    }

                    override fun onDone(utteranceId: String?) {
                        mainHandler.post {
                            _isSpeaking.value = false
                            _speakingMessageId.value = null
                        }
                    }

                    override fun onError(utteranceId: String?) {
                        mainHandler.post {
                            _isSpeaking.value = false
                            _speakingMessageId.value = null
                        }
                    }
                })
                isTtsInitialized = true
            }
        }
    }

    /** Inicia a escuta por voz via SpeechRecognizer nativo no Main Thread */
    fun startListening(onResult: (String) -> Unit) {
        // Pausa qualquer fala da IA antes de começar a escutar
        stopSpeaking()

        onSpeechResultCallback = onResult
        _spokenText.value = ""
        _voiceRms.value = 0.1f

        mainHandler.post {
            try {
                if (!SpeechRecognizer.isRecognitionAvailable(context)) {
                    _isListening.value = false
                    return@post
                }

                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context).apply {
                    setRecognitionListener(createRecognitionListener())
                }

                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "pt-BR")
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                }

                speechRecognizer?.startListening(intent)
                _isListening.value = true
            } catch (e: Exception) {
                _isListening.value = false
            }
        }
    }

    /** Interrompe a escuta e processa o que foi capturado */
    fun stopListening() {
        mainHandler.post {
            try {
                speechRecognizer?.stopListening()
            } catch (e: Exception) {
                // Ignore
            } finally {
                _isListening.value = false
            }
        }
    }

    /** Finaliza a sessão de voz e limpa o texto para fechar a interface imediatamente */
    fun finishVoiceSession() {
        onSpeechResultCallback = null
        mainHandler.post {
            try {
                speechRecognizer?.cancel()
            } catch (e: Exception) {
                // Ignore
            } finally {
                _isListening.value = false
                _spokenText.value = ""
                _voiceRms.value = 0.05f
            }
        }
    }

    /** Cancela a escuta sem emitir resultados */
    fun cancelListening() {
        finishVoiceSession()
    }

    private fun createRecognitionListener(): RecognitionListener {
        return object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                _isListening.value = true
            }

            override fun onBeginningOfSpeech() {}

            override fun onRmsChanged(rmsdB: Float) {
                // Normaliza o volume do microfone de -2dB..10dB para 0.1f..1.0f para animação do Orbe
                val normalized = ((rmsdB + 2f) / 12f).coerceIn(0.1f, 1.0f)
                _voiceRms.value = normalized
            }

            override fun onBufferReceived(buffer: ByteArray?) {}

            override fun onEndOfSpeech() {
                _voiceRms.value = 0.1f
            }

            override fun onError(error: Int) {
                mainHandler.post {
                    _isListening.value = false
                    _voiceRms.value = 0.1f
                }
            }

            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val text = matches?.firstOrNull()?.trim() ?: ""
                _spokenText.value = text
                _isListening.value = false
                _voiceRms.value = 0.05f
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                matches?.firstOrNull()?.let {
                    _spokenText.value = it
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) {}
        }
    }

    /** Lê a resposta da AURA em voz alta sintetizada em português */
    fun speak(messageId: String, rawText: String) {
        if (!isTtsInitialized || tts == null) return

        if (_isSpeaking.value && _speakingMessageId.value == messageId) {
            stopSpeaking()
            return
        }

        stopSpeaking()

        val cleanText = sanitizeTextForSpeech(rawText)
        if (cleanText.isBlank()) return

        _speakingMessageId.value = messageId
        _isSpeaking.value = true
        tts?.speak(cleanText, TextToSpeech.QUEUE_FLUSH, null, messageId)
    }

    /** Interrompe qualquer reprodução de áudio ativa */
    fun stopSpeaking() {
        if (_isSpeaking.value) {
            tts?.stop()
            _isSpeaking.value = false
            _speakingMessageId.value = null
        }
    }

    /** Converte markdown e termos técnicos do posto em texto falado fluido */
    private fun sanitizeTextForSpeech(text: String): String {
        var clean = text
            // Remove blocos de código e JSON
            .replace(Regex("```[\\s\\S]*?```"), "")
            .replace(Regex("`[^`]*`"), "")
            // Remove links markdown [label](url) -> label
            .replace(Regex("\\[([^\\]]+)\\]\\([^\\)]+\\)"), "$1")
            // Remove cabeçalhos e formatações markdown
            .replace(Regex("#+\\s*"), "")
            .replace(Regex("\\*\\*([^*]+)\\*\\*"), "$1")
            .replace(Regex("\\*([^*]+)\\*"), "$1")
            .replace(Regex("__([^_]+)__"), "$1")
            .replace(Regex("_([^_]+)_"), "$1")
            .replace(Regex("^[\\s]*[-*•]\\s*", RegexOption.MULTILINE), "")
            .replace("\u258A", "") // Cursor piscante
            // Pronúncia natural de siglas do posto
            .replace(Regex("\\bANP\\b", RegexOption.IGNORE_CASE), "A.N.P.")
            .replace(Regex("\\bLMC\\b", RegexOption.IGNORE_CASE), "L.M.C.")
            .replace(Regex("\\bPDV\\b", RegexOption.IGNORE_CASE), "P.D.V.")
            .replace(Regex("\\bTEF\\b", RegexOption.IGNORE_CASE), "T.E.F.")
            .replace(Regex("\\bKPI\\b", RegexOption.IGNORE_CASE), "K.P.I.")
            .replace(Regex("\\bERP\\b", RegexOption.IGNORE_CASE), "E.R.P.")
            .replace(" R$ ", " reais ")
            .replace(" L ", " litros ")
            .replace(" h ", " horas ")
            .trim()

        return clean
    }

    fun release() {
        mainHandler.post {
            speechRecognizer?.destroy()
            speechRecognizer = null
            tts?.stop()
            tts?.shutdown()
            tts = null
        }
    }
}
