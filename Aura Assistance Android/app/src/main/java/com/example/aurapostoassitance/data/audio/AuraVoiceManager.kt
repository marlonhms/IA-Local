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
    @param:ApplicationContext private val context: Context,
    val commandRouter: AuraVoiceCommandRouter
) {
    private val mainHandler = Handler(Looper.getMainLooper())

    // --- StateFlows para UI reativa ---
    private val _isListening = MutableStateFlow(false)
    val isListening: StateFlow<Boolean> = _isListening.asStateFlow()

    private val _spokenText = MutableStateFlow("")
    val spokenText: StateFlow<String> = _spokenText.asStateFlow()

    private val _voiceRms = MutableStateFlow(0.05f)
    val voiceRms: StateFlow<Float> = _voiceRms.asStateFlow()
    val voiceAmplitude: StateFlow<Float> = _voiceRms.asStateFlow()

    private val _isSpeaking = MutableStateFlow(false)
    val isSpeaking: StateFlow<Boolean> = _isSpeaking.asStateFlow()

    private val _speakingMessageId = MutableStateFlow<String?>(null)
    val speakingMessageId: StateFlow<String?> = _speakingMessageId.asStateFlow()

    private val _voiceError = MutableStateFlow<String?>(null)
    val voiceError: StateFlow<String?> = _voiceError.asStateFlow()

    private var speechRmsPulseRunnable: Runnable? = null

    private var speechRecognizer: SpeechRecognizer? = null
    private var onSpeechResultCallback: ((String) -> Unit)? = null
    private var lastPartialText: String = ""

    private var tts: TextToSpeech? = null
    private var isTtsInitialized = false
    private var pendingSpeech: Triple<String, String, (() -> Unit)?>? = null
    private var onSpeechFinishedCallback: Pair<String, () -> Unit>? = null

    init {
        initTts()
    }

    private fun initTts() {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale("pt", "BR")
                tts?.setPitch(1.03f)
                tts?.setSpeechRate(1.04f) // Cadência conversacional natural

                // Seleciona a melhor voz neural pt-BR instalada
                try {
                    val ptBrVoices = tts?.voices?.filter { it.locale.language == "pt" && it.locale.country == "BR" }
                    val highQualityVoice = ptBrVoices?.firstOrNull { 
                        it.name.contains("network") || it.name.contains("neural") || it.quality >= android.speech.tts.Voice.QUALITY_VERY_HIGH 
                    } ?: ptBrVoices?.firstOrNull()
                    if (highQualityVoice != null) {
                        tts?.voice = highQualityVoice
                    }
                } catch (_: Exception) {}

                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {
                        mainHandler.post {
                            if (utteranceId == null || utteranceId == _speakingMessageId.value) {
                                _isSpeaking.value = true
                                startSpeakingAmplitudePulse()
                            }
                        }
                    }

                    override fun onDone(utteranceId: String?) {
                        mainHandler.post {
                            if (utteranceId != null && utteranceId != _speakingMessageId.value) return@post
                            stopSpeakingAmplitudePulse()
                            _isSpeaking.value = false
                            _speakingMessageId.value = null
                            runCatching {
                                com.example.aurapostoassitance.service.AuraVoicePlaybackService.stopPlayback(context)
                            }
                            val finished = onSpeechFinishedCallback
                            if (finished != null && (utteranceId == null || finished.first == utteranceId)) {
                                onSpeechFinishedCallback = null
                                finished.second.invoke()
                            }
                        }
                    }

                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) {
                        mainHandler.post {
                            if (utteranceId != null && utteranceId != _speakingMessageId.value) return@post
                            onSpeechFinishedCallback = null
                            stopSpeakingAmplitudePulse()
                            _isSpeaking.value = false
                            _speakingMessageId.value = null
                            runCatching {
                                com.example.aurapostoassitance.service.AuraVoicePlaybackService.stopPlayback(context)
                            }
                        }
                    }

                    override fun onError(utteranceId: String?, errorCode: Int) {
                        mainHandler.post {
                            if (utteranceId != null && utteranceId != _speakingMessageId.value) return@post
                            onSpeechFinishedCallback = null
                            stopSpeakingAmplitudePulse()
                            _isSpeaking.value = false
                            _speakingMessageId.value = null
                            runCatching {
                                com.example.aurapostoassitance.service.AuraVoicePlaybackService.stopPlayback(context)
                            }
                        }
                    }
                })
                isTtsInitialized = true
                pendingSpeech?.let { (pendingId, pendingText, pendingDone) ->
                    pendingSpeech = null
                    mainHandler.post { speak(pendingId, pendingText, pendingDone) }
                }
            }
        }
    }

    private fun startSpeakingAmplitudePulse() {
        stopSpeakingAmplitudePulse()
        speechRmsPulseRunnable = object : Runnable {
            override fun run() {
                if (_isSpeaking.value) {
                    val t = System.currentTimeMillis() / 90.0
                    val harmonic = (0.35f + 0.45f * kotlin.math.abs(kotlin.math.sin(t)).toFloat()).coerceIn(0.1f, 1.0f)
                    _voiceRms.value = harmonic
                    mainHandler.postDelayed(this, 50)
                } else {
                    _voiceRms.value = 0.05f
                }
            }
        }
        mainHandler.post(speechRmsPulseRunnable!!)
    }

    private fun stopSpeakingAmplitudePulse() {
        speechRmsPulseRunnable?.let { mainHandler.removeCallbacks(it) }
        speechRmsPulseRunnable = null
        if (!_isListening.value) {
            _voiceRms.value = 0.05f
        }
    }

    fun clearVoiceError() {
        _voiceError.value = null
    }

    /** Inicia a escuta por voz via SpeechRecognizer nativo no Main Thread */
    fun startListening(onResult: (String) -> Unit) {
        // Pausa qualquer fala da IA antes de começar a escutar
        stopSpeaking()

        onSpeechResultCallback = onResult
        lastPartialText = ""
        _spokenText.value = ""
        _voiceError.value = null
        _voiceRms.value = 0.1f

        mainHandler.post {
            try {
                if (!SpeechRecognizer.isRecognitionAvailable(context)) {
                    _isListening.value = false
                    _voiceError.value = "Reconhecimento de voz indisponível neste dispositivo."
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
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1400L)
                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1100L)
                }

                speechRecognizer?.startListening(intent)
                _isListening.value = true
            } catch (e: Exception) {
                _isListening.value = false
                _voiceError.value = "Erro ao iniciar microfone: ${e.localizedMessage ?: "desconhecido"}"
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
        lastPartialText = ""
        mainHandler.post {
            try {
                speechRecognizer?.cancel()
            } catch (e: Exception) {
                // Ignore
            } finally {
                _isListening.value = false
                _spokenText.value = ""
                _voiceError.value = null
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
                    _voiceRms.value = 0.05f
                    val recovered = lastPartialText.trim().ifBlank { _spokenText.value.trim() }
                    val cb = onSpeechResultCallback
                    onSpeechResultCallback = null
                    lastPartialText = ""

                    if (recovered.isNotBlank() && cb != null) {
                        _spokenText.value = recovered
                        cb.invoke(recovered)
                        return@post
                    }

                    if (_spokenText.value.isBlank()) {
                        _voiceError.value = when (error) {
                            SpeechRecognizer.ERROR_NO_MATCH -> "Não consegui ouvir sua fala. Toque no Orbe para falar."
                            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Nenhuma fala detectada. Toque no Orbe para falar."
                            SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Microfone ocupado no momento. Tente novamente."
                            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Permissão de microfone não concedida."
                            SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Falha de rede no reconhecimento de voz."
                            else -> "Erro ao capturar áudio (código $error)."
                        }
                    }
                }
            }

            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val text = matches?.firstOrNull()?.trim().orEmpty().ifBlank {
                    lastPartialText.trim().ifBlank { _spokenText.value.trim() }
                }
                lastPartialText = ""
                _spokenText.value = text
                _isListening.value = false
                _voiceRms.value = 0.05f
                if (text.isNotBlank()) {
                    val cb = onSpeechResultCallback
                    onSpeechResultCallback = null
                    cb?.invoke(text)
                }
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                matches?.firstOrNull()?.let { partial ->
                    if (partial.isNotBlank()) {
                        lastPartialText = partial
                    }
                    _spokenText.value = partial
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) {}
        }
    }

    /** Lê a resposta da AURA em voz alta sintetizada em português */
    fun speak(messageId: String, rawText: String, onFinished: (() -> Unit)? = null) {
        if (!isTtsInitialized || tts == null) {
            pendingSpeech = Triple(messageId, rawText, onFinished)
            return
        }

        if (_isSpeaking.value && _speakingMessageId.value == messageId) {
            stopSpeaking()
            return
        }

        stopSpeaking()

        val cleanText = sanitizeTextForSpeech(rawText)
        if (cleanText.isBlank()) {
            onFinished?.invoke()
            return
        }

        onSpeechFinishedCallback = if (onFinished != null) (messageId to onFinished) else null
        _speakingMessageId.value = messageId
        _isSpeaking.value = true

        runCatching {
            val title = if (messageId.contains("briefing")) "Briefing Executivo Matinal (45s)" else "Conversa Executiva AURA"
            val sub = cleanText.take(55).trim() + "..."
            com.example.aurapostoassitance.service.AuraVoicePlaybackService.startPlayback(context, title, sub)
        }

        val speakResult = tts?.speak(cleanText, TextToSpeech.QUEUE_FLUSH, null, messageId)
        if (speakResult == TextToSpeech.ERROR) {
            stopSpeaking()
            onFinished?.invoke()
        }
    }

    /** Interrompe qualquer reprodução de áudio ativa */
    fun stopSpeaking() {
        onSpeechFinishedCallback = null
        stopSpeakingAmplitudePulse()
        if (_isSpeaking.value) {
            tts?.stop()
            _isSpeaking.value = false
            _speakingMessageId.value = null
            runCatching {
                com.example.aurapostoassitance.service.AuraVoicePlaybackService.stopPlayback(context)
            }
        }
    }

    /** Converte markdown e termos técnicos do posto em texto falado fluido */
    private fun sanitizeTextForSpeech(text: String): String {
        val clean = text
            // Remove blocos de código e JSON
            .replace(Regex("```[\\s\\S]*?```"), "")
            .replace(Regex("`[^`]*`"), "")
            // Remove tabelas e separadores markdown
            .replace(Regex("^\\s*\\|.*\\|\\s*$", RegexOption.MULTILINE), "")
            .replace(Regex("^\\s*[-*_]{3,}\\s*$", RegexOption.MULTILINE), "")
            // Remove links markdown [label](url) -> label
            .replace(Regex("\\[([^\\]]+)\\]\\([^\\)]+\\)"), "$1")
            // Remove cabeçalhos e formatações markdown
            .replace(Regex("#+\\s*"), "")
            .replace(Regex("\\*\\*([^*]+)\\*\\*"), "$1")
            .replace(Regex("\\*([^*]+)\\*"), "$1")
            .replace(Regex("__([^_]+)__"), "$1")
            .replace(Regex("_([^_]+)_"), "$1")
            .replace(Regex("^[\\s]*[-*•]\\s*", RegexOption.MULTILINE), "")
            // Remove emojis e símbolos decorativos para o TTS não soletrar ícones
            .replace(Regex("[\\uD83C-\\uDBFF\\uDC00-\\uDFFF]+"), "")
            .replace(Regex("[\\u2600-\\u27BF\\uFE0F]"), "")
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
            .replace(Regex("\\n+"), ". ")
            .replace(Regex("\\s{2,}"), " ")
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
