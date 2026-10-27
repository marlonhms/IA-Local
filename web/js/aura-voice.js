/**
 * Controlador de Entrada Rapida por Voz da AURA (Experiencia Imersiva estilo Gemini / GPT)
 * Utiliza o motor gratuito de alta velocidade Groq Whisper Cloud (/api/v1/aura/voice/transcribe)
 * com captura de audio via HTML5 MediaRecorder e reatividade fluida do AuraLivingOrb a 60 FPS.
 * Regra inegociavel: ZERO travessoes e total tolerancia a falhas de hardware/permissao.
 */

class AuraVoiceController {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.mediaStream = null;
    this.isListening = false;
    this.isTranscribing = false;
    this.supported = false;
    this.autoSend = false;
    this.voiceStatus = null;
    this.currentTranscript = '';

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

    const hasMedia = Boolean(
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === 'function' &&
      typeof window.MediaRecorder !== 'undefined'
    );

    this.supported = hasMedia;

    if (this.btnVoice) {
      this.btnVoice.addEventListener('click', (e) => {
        if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
        this.toggleVoice();
      });
    }

    this.bindModalEvents();
    this.checkBackendVoiceStatus();
  }

  /**
   * Consulta o status do servico Groq Whisper no backend
   */
  async checkBackendVoiceStatus() {
    try {
      const resp = await fetch('/api/v1/aura/voice/status');
      if (resp.ok) {
        this.voiceStatus = await resp.json();
      }
    } catch (_) {
      // Falha silenciosa de probe no startup
    }
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
      this.previewText.textContent = 'AURA esta ouvindo... Fale seu comando e clique em Concluir quando terminar';
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
   * Inicia gravacao de audio via HTML5 MediaRecorder e conecta ao AuraLivingOrb
   */
  async startListening() {
    if (!this.supported) {
      const msg = 'Gravacao de microfone nao suportada neste navegador. Digite seu comando.';
      this.announce(msg);
      if (this.chatInput) this.chatInput.focus();
      return;
    }

    try {
      this.audioChunks = [];
      this.isListening = true;
      this.isTranscribing = false;
      this.openVoiceModal();
      this.announce('Ouvindo comando de pista... Fale agora.');

      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // Conecta analisador Web Audio do Orbe para reagir as ondas de audio em tempo real
      if (window.auraOrbManager) {
        window.auraOrbManager.attachAudioStream(this.mediaStream);
        window.auraOrbManager.setEmotion('LISTENING');
      }

      // Detecta formato suportado pelo navegador
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

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.start(250);

      if (window.auraAudio && typeof window.auraAudio.playChime === 'function') {
        window.auraAudio.playChime(640, 0.05);
      }
    } catch (err) {
      console.warn('[AURA Voice] Falha ao obter microfone:', err);
      this.isListening = false;
      this.cleanupMediaStream();

      let msg = 'Erro no microfone ou permissao negada no navegador.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        msg = 'Permissao de microfone negada. Autorize o microfone no cadeado da barra de endereco.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        msg = 'Nenhum microfone encontrado neste computador.';
      }

      if (this.statusLabel) {
        this.statusLabel.textContent = 'ATENCAO OPERACIONAL';
        this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-400';
      }

      if (this.previewText) {
        this.previewText.textContent = msg;
        this.previewText.className = 'text-sm font-sans text-amber-300 leading-relaxed';
      }

      if (window.auraOrbManager) {
        window.auraOrbManager.setEmotion('WORRIED');
      }

      this.announce(msg);
      setTimeout(() => {
        if (!this.isListening && !this.currentTranscript) {
          this.closeVoiceModal();
        }
      }, 5000);
    }
  }

  /**
   * Conclui a gravacao de audio e envia para o backend transcrever via Groq Whisper
   */
  commitAndSendVoice() {
    if (!this.isListening || !this.mediaRecorder) {
      if (this.currentTranscript && this.chatInput) {
        this.closeVoiceModal();
        const sendBtn = document.getElementById('btn-chat-send');
        if (sendBtn) sendBtn.click();
      }
      return;
    }

    this.isListening = false;
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

    this.mediaRecorder.onstop = async () => {
      try {
        const mime = this.mediaRecorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(this.audioChunks, { type: mime });
        this.cleanupMediaStream();

        if (audioBlob.size < 400) {
          if (this.statusLabel) {
            this.statusLabel.textContent = 'ATENCAO OPERACIONAL';
            this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-400';
          }
          if (this.previewText) {
            this.previewText.textContent = 'Gravacao muito curta. Fale mais proximo ao microfone e tente novamente.';
            this.previewText.className = 'text-sm font-sans text-amber-300';
          }
          if (window.auraOrbManager) window.auraOrbManager.setEmotion('WORRIED');
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
            this.statusLabel.textContent = response.status === 503 ? 'CONFIGURACAO NECESSARIA' : 'ATENCAO OPERACIONAL';
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

        const recognizedText = String(data.text || '').trim();
        this.currentTranscript = recognizedText;
        this.isTranscribing = false;

        if (recognizedText) {
          if (this.chatInput) {
            this.chatInput.value = recognizedText;
            this.chatInput.dispatchEvent(new Event('input', { bubbles: true }));
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = `${Math.min(this.chatInput.scrollHeight, 160)}px`;
          }

          if (this.previewText) {
            this.previewText.textContent = `"${recognizedText}"`;
            this.previewText.className = 'text-base sm:text-lg font-sans font-semibold text-white tracking-wide transition-all';
          }

          if (this.statusLabel) {
            const timeInfo = data.duration_ms ? ` (${data.duration_ms}ms)` : '';
            this.statusLabel.textContent = `TRANSCRICAO CONCLUIDA${timeInfo}`;
            this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-emerald-400';
          }

          if (window.auraOrbManager) {
            window.auraOrbManager.setEmotion('SUCCESS');
          }

          this.announce(`Comando reconhecido: ${recognizedText}`);

          // Dispara o envio imediato para o chat
          setTimeout(() => {
            this.closeVoiceModal();
            if (this.chatInput && this.chatInput.value.trim()) {
              this.chatInput.focus();
              const sendBtn = document.getElementById('btn-chat-send');
              if (sendBtn) {
                sendBtn.click();
              }
            }
          }, 650);
        } else {
          if (this.statusLabel) {
            this.statusLabel.textContent = 'NENHUMA FALA DETECTADA';
            this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-400';
          }
          if (this.previewText) {
            this.previewText.textContent = 'Nao foi possivel identificar palavras na gravacao. Fale novamente.';
            this.previewText.className = 'text-sm font-sans text-amber-300';
          }
          if (window.auraOrbManager) window.auraOrbManager.setEmotion('CALM');
        }
      } catch (err) {
        console.error('[AURA Voice] Erro ao comunicar com endpoint de voz:', err);
        this.isTranscribing = false;
        if (this.statusLabel) {
          this.statusLabel.textContent = 'FALHA DE REDE';
          this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-red-400';
        }
        if (this.previewText) {
          this.previewText.textContent = 'Nao foi possivel conectar ao servidor da AURA para transcrever o audio.';
          this.previewText.className = 'text-sm font-sans text-red-300';
        }
        if (window.auraOrbManager) window.auraOrbManager.setEmotion('WORRIED');
      }
    };

    try {
      this.mediaRecorder.stop();
    } catch (_) {}
  }

  /**
   * Cancela a sessao de voz sem enviar
   */
  cancelVoiceSession() {
    this.isListening = false;
    this.isTranscribing = false;
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
   * Interrompe o reconhecimento ativo
   */
  stopListening() {
    this.cancelVoiceSession();
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
