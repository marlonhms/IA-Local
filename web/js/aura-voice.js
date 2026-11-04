/**
 * Controlador de Entrada Rapida por Voz da AURA (Experiencia Imersiva estilo Gemini / GPT)
 * Arquitetura Hibrida Dual-Engine:
 * 1. Motor Primario: Web Speech API em tempo real (streaming de palavras enquanto o operador fala).
 * 2. Motor Secundario (Fallback): Groq Whisper Cloud (/api/v1/aura/voice/transcribe) via MediaRecorder.
 * 3. Reatividade fluida do AuraLivingOrb a 60 FPS sem conflito de hardware.
 * Regra inegociavel: ZERO travessoes e total tolerancia a falhas de hardware/permissao.
 */

class AuraVoiceController {
  constructor() {
    this.recognition = null;
    this.mediaRecorder = null;
    this.mediaStream = null;
    this.audioChunks = [];
    this.isListening = false;
    this.isTranscribing = false;
    this.speechRecognitionActive = false;
    this.autoSend = false;
    this.currentTranscript = '';
    this.silenceTimer = null;

    // Elementos da interface
    this.btnVoice = null;
    this.chatInput = null;
    this.announcer = null;

    // Elementos do Modal Imersivo de Voz
    this.modal = null;
    this.modalCard = null;
    this.modalOrbContainer = null;
    this.modalOrb = null;
    this.previewText = null;
    this.statusLabel = null;
    this.btnClose = null;
    this.btnSend = null;
    this.btnClear = null;
    this.scrim = null;
  }

  /**
   * Permite configurar o envio automatico do comando de voz apos conclusao
   */
  setAutoSend(enabled) {
    this.autoSend = Boolean(enabled);
  }

  /**
   * Inicializa o suporte a gravacao e vincula os elementos da interface
   */
  init() {
    this.btnVoice = document.getElementById('btn-voice-input');
    this.chatInput = document.getElementById('chat-input-text');
    this.announcer = document.getElementById('aura-sr-announcer');

    // Elementos do Modal Imersivo
    this.modal = document.getElementById('aura-voice-modal-overlay');
    this.modalCard = document.getElementById('aura-voice-modal-card');
    this.modalOrbContainer = document.getElementById('aura-voice-modal-orb-container');
    this.previewText = document.getElementById('aura-voice-transcription-preview');
    this.statusLabel = document.getElementById('aura-voice-status-label');
    this.btnClose = document.getElementById('btn-voice-modal-close');
    this.btnSend = document.getElementById('btn-voice-modal-send');
    this.btnClear = document.getElementById('btn-voice-modal-clear');
    this.scrim = document.getElementById('aura-voice-scrim');

    // Instancia Web Speech API se disponivel no navegador
    const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognitionClass) {
      try {
        this.recognition = new SpeechRecognitionClass();
        this.recognition.lang = 'pt-BR';
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 1;
        this.bindRecognitionEvents();
      } catch (err) {
        console.warn('[AURA Voice] Falha ao instanciar SpeechRecognition nativo:', err);
        this.recognition = null;
      }
    }

    if (this.btnVoice) {
      this.btnVoice.addEventListener('click', (e) => {
        if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
        this.toggleVoice();
      });
    }

    this.bindModalEvents();
  }

  /**
   * Vincula eventos de escuta em tempo real do Web Speech API
   */
  bindRecognitionEvents() {
    if (!this.recognition) return;

    this.recognition.onstart = () => {
      this.speechRecognitionActive = true;
      if (this.statusLabel && this.isListening) {
        this.statusLabel.textContent = 'AURA SINTONIZADA • OUVINDO';
        this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-cyan-300';
      }
    };

    this.recognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = 0; i < event.results.length; ++i) {
        const item = event.results[i];
        if (item.isFinal) {
          finalTranscript += item[0].transcript;
        } else {
          interimTranscript += item[0].transcript;
        }
      }

      const recognized = (finalTranscript + interimTranscript).trim();
      if (recognized) {
        this.currentTranscript = recognized;

        if (this.chatInput) {
          this.chatInput.value = recognized;
          this.chatInput.dispatchEvent(new Event('input', { bubbles: true }));
          this.chatInput.style.height = 'auto';
          this.chatInput.style.height = `${Math.min(this.chatInput.scrollHeight, 160)}px`;
        }

        if (this.previewText) {
          this.previewText.textContent = `"${recognized}"`;
          this.previewText.className = 'text-base sm:text-lg font-sans font-semibold text-white tracking-wide transition-all';
        }

        if (this.statusLabel) {
          this.statusLabel.textContent = 'AURA TRANSCREVENDO EM TEMPO REAL';
          this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-cyan-400';
        }

        // Reinicia timer de pausa para conclusao natural
        this.resetSilenceTimer();
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('[AURA Voice] Web Speech API aviso/erro:', event.error);
      this.speechRecognitionActive = false;

      // Se for erro de rede, o fallback Groq Whisper assume automaticamente no commit
      if (event.error === 'network') {
        if (this.statusLabel && this.isListening) {
          this.statusLabel.textContent = 'OUVINDO VIA RECONHECEDOR DE ALTA PRECISÃO';
          this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-purple-300';
        }
      }
    };

    this.recognition.onend = () => {
      this.speechRecognitionActive = false;
    };
  }

  /**
   * Vincula os eventos de interacao do Modal de Voz
   */
  bindModalEvents() {
    if (this.btnClose) {
      this.btnClose.addEventListener('click', () => {
        this.cancelVoiceSession();
      });
    }

    if (this.scrim) {
      this.scrim.addEventListener('click', () => {
        this.cancelVoiceSession();
      });
    }

    if (this.btnClear) {
      this.btnClear.addEventListener('click', () => {
        this.currentTranscript = '';
        if (this.chatInput) this.chatInput.value = '';
        if (this.previewText) {
          this.previewText.textContent = 'AURA esta ouvindo... Fale sobre bombas, tanques ou auditoria fiscal';
          this.previewText.className = 'text-sm sm:text-base font-sans text-slate-400 transition-colors leading-relaxed';
        }
      });
    }

    if (this.btnSend) {
      this.btnSend.addEventListener('click', () => {
        this.commitAndSendVoice();
      });
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && (this.isListening || this.isTranscribing) && this.modal && !this.modal.classList.contains('hidden')) {
        this.cancelVoiceSession();
      }
    });
  }

  /**
   * Abre o Modal Imersivo de Voz: fundo escurece e o orbe sobe flutuando
   */
  openVoiceModal() {
    if (!this.modal) return;

    this.currentTranscript = '';
    this.modal.classList.remove('hidden');

    requestAnimationFrame(() => {
      this.modal.classList.add('modal-active');
    });

    if (this.statusLabel) {
      this.statusLabel.textContent = 'AURA SINTONIZADA • OUVINDO';
      this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-cyan-300';
    }

    if (this.previewText) {
      this.previewText.textContent = 'AURA esta ouvindo... Fale seu comando de pista';
      this.previewText.className = 'text-sm sm:text-base font-sans text-slate-300 transition-colors leading-relaxed';
    }

    // Instancia o Orbe Vivo Majestoso (140px, paridade AuraVoiceOrbSheet)
    if (this.modalOrbContainer && window.AuraOrb) {
      if (this.modalOrb) {
        this.modalOrb.destroy();
      }
      this.modalOrb = new window.AuraOrb({
        container: this.modalOrbContainer,
        size: 140,
        emotion: 'LISTENING',
        isInteractive: false
      });
      if (window.auraOrbManager) {
        window.auraOrbManager.registerOrb('modal-voice', this.modalOrb);
      }
    }
  }

  /**
   * Fecha o Modal Imersivo de Voz suavemente
   */
  closeVoiceModal() {
    if (!this.modal) return;

    this.modal.classList.remove('modal-active');

    setTimeout(() => {
      if (!this.isListening && !this.isTranscribing && this.modal) {
        this.modal.classList.add('hidden');
      }
      if (this.modalOrb) {
        if (window.auraOrbManager) {
          window.auraOrbManager.unregisterOrb('modal-voice');
        }
        this.modalOrb.destroy();
        this.modalOrb = null;
      }
    }, 320);
  }

  /**
   * Inicia escuta hibrida (Web Speech API em tempo real + gravador MediaRecorder)
   */
  async startListening() {
    try {
      this.audioChunks = [];
      this.isListening = true;
      this.isTranscribing = false;
      this.currentTranscript = '';
      this.openVoiceModal();
      this.announce('Ouvindo comando de pista... Fale agora.');

      // 1. Inicia Web Speech API nativo para streaming instantaneo de palavras
      if (this.recognition) {
        try {
          this.recognition.start();
        } catch (err) {
          console.warn('[AURA Voice] Falha ao iniciar recognition:', err);
        }
      }

      // 2. Conecta stream de microfone para o Orbe pulsar a 60 FPS e para o gravador
      if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function') {
        try {
          this.mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true
            }
          });

          if (window.auraOrbManager && this.isListening) {
            window.auraOrbManager.attachAudioStream(this.mediaStream);
            window.auraOrbManager.setEmotion('LISTENING');
          }

          // Inicia gravador de audio para fallback no Groq Whisper
          if (typeof window.MediaRecorder !== 'undefined') {
            let mimeType = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
              if (MediaRecorder.isTypeSupported('audio/webm')) {
                mimeType = 'audio/webm';
              } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
                mimeType = 'audio/ogg;codecs=opus';
              } else {
                mimeType = '';
              }
            }

            this.mediaRecorder = mimeType
              ? new MediaRecorder(this.mediaStream, { mimeType })
              : new MediaRecorder(this.mediaStream);

            this.mediaRecorder.ondataavailable = (e) => {
              if (e.data && e.data.size > 0) {
                this.audioChunks.push(e.data);
              }
            };

            this.mediaRecorder.start(250);
          }
        } catch (micErr) {
          console.warn('[AURA Voice] Permissao de gravacao auxiliar opcional:', micErr);
        }
      }

      if (window.auraAudio && typeof window.auraAudio.playChime === 'function') {
        window.auraAudio.playChime(640, 0.05);
      }
    } catch (err) {
      console.warn('[AURA Voice] Erro ao iniciar escuta de voz:', err);
      this.cancelVoiceSession();
    }
  }

  /**
   * Reinicia temporizador de silencio para envio automatico com pausa na fala
   */
  resetSilenceTimer() {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
    }
    // Conclui e envia apos 1.8 segundos de pausa na fala
    this.silenceTimer = setTimeout(() => {
      if (this.isListening && this.currentTranscript.trim()) {
        this.commitAndSendVoice();
      }
    }, 1800);
  }

  /**
   * Conclui a sessao de voz e envia imediatamente
   */
  async commitAndSendVoice() {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }

    if (!this.isListening && !this.isTranscribing) return;

    this.isListening = false;

    // Se o Web Speech API ja transcreveu em tempo real, despacha imediatamente
    if (this.currentTranscript.trim()) {
      this.finalizeAndSend(this.currentTranscript.trim());
      return;
    }

    // Caso contrario, recorre ao motor Groq Whisper usando o audio gravado
    this.isTranscribing = true;

    if (this.statusLabel) {
      this.statusLabel.textContent = 'PROCESSANDO COM GROQ WHISPER...';
      this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-300 animate-pulse';
    }

    if (this.previewText) {
      this.previewText.textContent = 'Transcrevendo comando de pista com alta velocidade...';
      this.previewText.className = 'text-sm font-sans text-amber-200 animate-pulse';
    }

    if (window.auraOrbManager) {
      window.auraOrbManager.setEmotion('THINKING');
    }

    // Finaliza gravador de audio e processa
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try {
        if (typeof this.mediaRecorder.requestData === 'function') {
          this.mediaRecorder.requestData();
        }
      } catch (_) {}

      this.mediaRecorder.onstop = async () => {
        await this.sendAudioToGroqWhisper();
      };

      try {
        this.mediaRecorder.stop();
      } catch (_) {
        await this.sendAudioToGroqWhisper();
      }
    } else {
      await this.sendAudioToGroqWhisper();
    }
  }

  /**
   * Envia chunks de audio gravados para o endpoint local /api/v1/aura/voice/transcribe
   */
  async sendAudioToGroqWhisper() {
    try {
      const mime = (this.mediaRecorder && this.mediaRecorder.mimeType) ? this.mediaRecorder.mimeType : 'audio/webm';
      const audioBlob = new Blob(this.audioChunks, { type: mime });
      this.cleanupMediaStream();

      if (audioBlob.size < 300) {
        if (this.statusLabel) {
          this.statusLabel.textContent = 'NENHUMA FALA IDENTIFICADA';
          this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-400';
        }
        if (this.previewText) {
          this.previewText.textContent = 'Fale seu comando mais proximo ao microfone e clique em Concluir.';
          this.previewText.className = 'text-sm font-sans text-amber-300';
        }
        if (window.auraOrbManager) window.auraOrbManager.setEmotion('CALM');
        this.isTranscribing = false;
        return;
      }

      const response = await fetch('/api/v1/aura/voice/transcribe', {
        method: 'POST',
        headers: {
          'Content-Type': mime
        },
        body: audioBlob
      });

      const data = await response.json();

      if (!response.ok) {
        const detail = data && data.detail ? data.detail : 'Falha na transcricao do audio.';
        if (this.statusLabel) {
          this.statusLabel.textContent = 'AVISO OPERACIONAL';
          this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-400';
        }
        if (this.previewText) {
          this.previewText.textContent = detail;
          this.previewText.className = 'text-sm font-sans text-amber-300 leading-relaxed';
        }
        if (window.auraOrbManager) window.auraOrbManager.setEmotion('WORRIED');
        this.isTranscribing = false;
        return;
      }

      const text = String(data.text || '').trim();
      this.isTranscribing = false;

      if (text) {
        this.finalizeAndSend(text, data.duration_ms);
      } else {
        if (this.statusLabel) {
          this.statusLabel.textContent = 'NENHUMA FALA DETECTADA';
          this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-400';
        }
        if (this.previewText) {
          this.previewText.textContent = 'Nao foi possivel identificar palavras no audio.';
          this.previewText.className = 'text-sm font-sans text-amber-300';
        }
        if (window.auraOrbManager) window.auraOrbManager.setEmotion('CALM');
      }
    } catch (err) {
      console.warn('[AURA Voice] Erro ao consultar Groq Whisper:', err);
      this.isTranscribing = false;
      this.cleanupMediaStream();
      if (this.statusLabel) {
        this.statusLabel.textContent = 'ATENCAO';
        this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-400';
      }
      if (this.previewText) {
        this.previewText.textContent = 'Nao foi possivel transcrever o comando de voz.';
        this.previewText.className = 'text-sm font-sans text-amber-300';
      }
      if (window.auraOrbManager) window.auraOrbManager.setEmotion('WORRIED');
    }
  }

  /**
   * Atualiza interface, preenche texto no chat e envia com feedback visual
   */
  finalizeAndSend(text, durationMs = null) {
    this.currentTranscript = text;
    this.cleanupMediaStream();

    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (_) {}
    }

    if (this.chatInput) {
      this.chatInput.value = text;
      this.chatInput.dispatchEvent(new Event('input', { bubbles: true }));
      this.chatInput.style.height = 'auto';
      this.chatInput.style.height = `${Math.min(this.chatInput.scrollHeight, 160)}px`;
    }

    if (this.previewText) {
      this.previewText.textContent = `"${text}"`;
      this.previewText.className = 'text-base sm:text-lg font-sans font-semibold text-white tracking-wide transition-all';
    }

    if (this.statusLabel) {
      const timeInfo = durationMs ? ` (${durationMs}ms)` : '';
      this.statusLabel.textContent = `TRANSCRICAO CONCLUIDA${timeInfo}`;
      this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-emerald-400';
    }

    if (window.auraOrbManager) {
      window.auraOrbManager.setEmotion('SUCCESS');
    }

    this.announce(`Comando reconhecido: ${text}`);

    setTimeout(() => {
      this.closeVoiceModal();
      if (this.chatInput && this.chatInput.value.trim()) {
        this.chatInput.focus();
        const sendBtn = document.getElementById('btn-chat-send');
        if (sendBtn) {
          sendBtn.click();
        }
      }
    }, 600);
  }

  /**
   * Cancela a sessao de voz sem enviar
   */
  cancelVoiceSession() {
    this.isListening = false;
    this.isTranscribing = false;

    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }

    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (_) {}
    }

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try {
        this.mediaRecorder.stop();
      } catch (_) {}
    }

    this.cleanupMediaStream();
    this.closeVoiceModal();

    if (this.chatInput) {
      this.chatInput.value = '';
    }
  }

  /**
   * Libera stream do microfone e desvincula analisador de audio
   */
  cleanupMediaStream() {
    if (this.mediaStream) {
      try {
        this.mediaStream.getTracks().forEach((track) => track.stop());
      } catch (_) {}
      this.mediaStream = null;
    }
    if (typeof window !== 'undefined' && window.auraOrbManager) {
      window.auraOrbManager.detachAudioStream();
    }
  }

  /**
   * Alterna entre iniciar gravacao ou concluir e transcrever
   */
  toggleVoice() {
    if (this.isListening) {
      this.commitAndSendVoice();
    } else {
      this.startListening();
    }
  }

  /**
   * Notifica leitores de tela acessiveis (WCAG 2.1 AA)
   */
  announce(text) {
    if (this.announcer) {
      this.announcer.textContent = text;
    }
  }
}

// Instancia global do controlador de voz
window.auraVoice = new AuraVoiceController();

document.addEventListener('DOMContentLoaded', () => {
  if (window.auraVoice) {
    window.auraVoice.init();
  }
});
