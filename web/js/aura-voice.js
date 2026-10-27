/**
 * Controlador de Entrada Rapida por Voz da AURA (Experiencia Imersiva estilo Gemini / GPT)
 * Ao acionar o microfone, o fundo escurece e o orbe sobe flutuando no centro da tela,
 * reagindo as ondas de audio em tempo real para gerar a transcricao.
 * Regra inegociavel: ZERO travessoes e total tolerancia a falhas de hardware/permissao.
 */

class AuraVoiceController {
  constructor() {
    this.recognition = null;
    this.isListening = false;
    this.supported = false;
    this.autoSend = false;
    this.btnVoice = null;
    this.chatInput = null;
    this.announcer = null;
    this.mediaStream = null;

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
    this.currentTranscript = '';
  }

  /**
   * Permite configurar o envio automatico do comando de voz apos conclusao
   */
  setAutoSend(enabled) {
    this.autoSend = Boolean(enabled);
  }

  /**
   * Inicializa o suporte a Web Speech API e vincula os elementos da interface
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

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'pt-BR';
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 1;
        this.supported = true;
        this.bindRecognitionEvents();
      } catch (err) {
        console.warn('[AURA Voice] Falha ao instanciar SpeechRecognition:', err);
        this.supported = false;
      }
    } else {
      this.supported = false;
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
      if (e.key === 'Escape' && this.isListening && this.modal && !this.modal.classList.contains('hidden')) {
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

    // Dispara transicao fluida
    requestAnimationFrame(() => {
      this.modal.classList.add('modal-active');
    });

    if (this.statusLabel) {
      this.statusLabel.textContent = 'AURA SINTONIZADA • OUVINDO';
      this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-cyan-300';
    }

    if (this.previewText) {
      this.previewText.textContent = 'AURA esta ouvindo... Fale sobre bombas, tanques ou auditoria fiscal';
      this.previewText.className = 'text-sm sm:text-base font-sans text-slate-400 transition-colors leading-relaxed';
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
      if (!this.isListening && this.modal) {
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
   * Conclui a transcricao de voz e envia imediatamente
   */
  commitAndSendVoice() {
    this.stopListening();
    this.closeVoiceModal();

    if (this.chatInput && this.chatInput.value.trim()) {
      this.chatInput.focus();
      const sendBtn = document.getElementById('btn-chat-send');
      if (sendBtn) {
        sendBtn.click();
      }
    }
  }

  /**
   * Cancela a sessao de voz sem enviar
   */
  cancelVoiceSession() {
    this.stopListening();
    this.closeVoiceModal();
    if (this.chatInput) {
      this.chatInput.value = '';
    }
  }

  /**
   * Configura os callbacks de escuta, transcricao e tratamento de erros
   */
  bindRecognitionEvents() {
    if (!this.recognition) return;

    this.recognition.onstart = () => {
      this.isListening = true;
      this.openVoiceModal();
      this.announce('Ouvindo comando de pista... Fale agora.');

      if (typeof window !== 'undefined' && window.auraOrbManager) {
        window.auraOrbManager.setEmotion('LISTENING');
      }

      // Conecta o analisador Web Audio ao microfone para reagir as ondas de audio em tempo real
      if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function') {
        navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
          if (this.isListening) {
            this.mediaStream = stream;
            if (typeof window !== 'undefined' && window.auraOrbManager) {
              window.auraOrbManager.attachAudioStream(stream);
            }
          } else {
            stream.getTracks().forEach((t) => t.stop());
          }
        }).catch((err) => {
          console.warn('[AURA Voice] Analisador Web Audio opcional indisponivel:', err);
        });
      }

      if (window.auraAudio && typeof window.auraAudio.playChime === 'function') {
        window.auraAudio.playChime(640, 0.05);
      }
    };

    this.recognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const item = event.results[i];
        if (item.isFinal) {
          finalTranscript += item[0].transcript;
        } else {
          interimTranscript += item[0].transcript;
        }
      }

      const recognizedText = (finalTranscript + interimTranscript).trim();
      this.currentTranscript = recognizedText;

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
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('[AURA Voice] Erro no reconhecimento:', event.error);
      this.isListening = false;
      this.cleanupMediaStream();

      let msg = 'Erro no microfone.';
      if (event.error === 'not-allowed') {
        msg = 'Permissao de microfone negada no navegador.';
      } else if (event.error === 'no-speech') {
        msg = 'Nenhum comando de voz detectado na pista.';
      } else if (event.error === 'network') {
        msg = 'Falha de rede no reconhecimento de voz.';
      }

      if (this.statusLabel) {
        this.statusLabel.textContent = 'ATENCAO OPERACIONAL';
        this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-amber-400';
      }

      if (this.previewText) {
        this.previewText.textContent = msg;
        this.previewText.className = 'text-sm font-sans text-amber-300';
      }

      if (typeof window !== 'undefined' && window.auraOrbManager) {
        window.auraOrbManager.setEmotion('WORRIED');
        setTimeout(() => {
          if (window.auraOrbManager && window.auraOrbManager.getEmotion() === 'WORRIED') {
            window.auraOrbManager.setEmotion('CALM');
          }
        }, 2500);
      }

      this.announce(msg);
      setTimeout(() => {
        this.closeVoiceModal();
      }, 2200);
    };

    this.recognition.onend = () => {
      this.isListening = false;
      this.cleanupMediaStream();
      this.announce('Comando de voz concluido.');

      if (this.statusLabel) {
        this.statusLabel.textContent = 'TRANSCRICAO CONCLUIDA';
        this.statusLabel.className = 'text-xs font-sans font-bold uppercase tracking-widest text-emerald-400';
      }

      if (typeof window !== 'undefined' && window.auraOrbManager) {
        window.auraOrbManager.setEmotion('CALM');
      }

      if (this.autoSend && this.currentTranscript.trim()) {
        setTimeout(() => {
          this.commitAndSendVoice();
        }, 400);
      }
    };
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
    this.isListening = false;
    this.cleanupMediaStream();
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (_) {}
    }
    if (typeof window !== 'undefined' && window.auraOrbManager) {
      window.auraOrbManager.setEmotion('CALM');
    }
  }

  /**
   * Alterna entre iniciar ou interromper a escuta
   */
  toggleVoice() {
    if (!this.supported || !this.recognition) {
      const msg = 'Reconhecimento de voz nao suportado neste navegador. Digite seu comando.';
      this.announce(msg);
      if (this.chatInput) this.chatInput.focus();
      return;
    }

    if (this.isListening) {
      this.commitAndSendVoice();
    } else {
      try {
        this.recognition.start();
      } catch (err) {
        this.isListening = false;
        this.cleanupMediaStream();
        console.warn('[AURA Voice] Erro ao iniciar SpeechRecognition:', err);
      }
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
