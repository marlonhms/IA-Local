/**
 * Controlador de Entrada Rapida por Voz da AURA (Fase P3-4: Web Speech API pt-BR)
 * Projetado para operacao na pista sob sol forte e uso com luvas.
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
    this.indicator = null;
    this.announcer = null;
  }

  /**
   * Permite configurar o envio automatico do comando de voz apos conclusao
   */
  setAutoSend(enabled) {
    this.autoSend = Boolean(enabled);
  }

  /**
   * Inicializa o suporte a Web Speech API e vincula os eventos da interface
   */
  init() {
    this.btnVoice = document.getElementById('btn-voice-input');
    this.chatInput = document.getElementById('chat-input-text');
    this.indicator = document.getElementById('voice-recording-indicator');
    this.announcer = document.getElementById('aura-sr-announcer');

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
  }

  /**
   * Configura os callbacks de escuta, transcricao e tratamento de erros
   */
  bindRecognitionEvents() {
    if (!this.recognition) return;

    this.recognition.onstart = () => {
      this.isListening = true;
      this.renderListeningState(true);
      this.announce('Ouvindo comando de pista... Fale agora.');
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

      if (recognizedText && this.chatInput) {
        this.chatInput.value = recognizedText;
        this.chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = `${Math.min(this.chatInput.scrollHeight, 160)}px`;
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('[AURA Voice] Erro no reconhecimento:', event.error);
      this.isListening = false;
      this.renderListeningState(false);

      let msg = 'Erro no microfone.';
      if (event.error === 'not-allowed') {
        msg = 'Permissao de microfone negada no navegador.';
      } else if (event.error === 'no-speech') {
        msg = 'Nenhum comando de voz detectado na pista.';
      } else if (event.error === 'network') {
        msg = 'Falha de rede no reconhecimento de voz.';
      }

      this.showFeedback(msg);
      this.announce(msg);
    };

    this.recognition.onend = () => {
      this.isListening = false;
      this.renderListeningState(false);
      this.announce('Comando de voz concluido.');
      if (this.chatInput && this.chatInput.value.trim()) {
        this.chatInput.focus();
        if (this.autoSend) {
          const sendBtn = document.getElementById('btn-chat-send');
          if (sendBtn) {
            sendBtn.click();
          }
        }
      }
    };
  }

  /**
   * Alterna entre iniciar ou interromper a escuta
   */
  toggleVoice() {
    if (!this.supported || !this.recognition) {
      const msg = 'Reconhecimento de voz nao suportado neste navegador. Digite seu comando.';
      this.showFeedback(msg);
      this.announce(msg);
      if (this.chatInput) this.chatInput.focus();
      return;
    }

    if (this.isListening) {
      this.isListening = false;
      try {
        this.recognition.stop();
      } catch (_) {}
      this.renderListeningState(false);
    } else {
      try {
        this.isListening = true;
        this.renderListeningState(true);
        this.recognition.start();
      } catch (err) {
        this.isListening = false;
        this.renderListeningState(false);
        console.warn('[AURA Voice] Erro ao iniciar SpeechRecognition:', err);
        this.showFeedback('Nao foi possivel acessar o microfone.');
      }
    }
  }

  /**
   * Atualiza o estado visual do botao de voz e do indicador HUD
   */
  renderListeningState(listening) {
    if (this.btnVoice) {
      this.btnVoice.setAttribute('aria-pressed', listening ? 'true' : 'false');
      if (listening) {
        this.btnVoice.classList.add('bg-rose-600', 'text-white', 'border-rose-400', 'voice-recording-pulsing');
        this.btnVoice.classList.remove('bg-slate-800', 'text-slate-300', 'border-slate-700');
        this.btnVoice.title = 'Parar escuta de voz';
      } else {
        this.btnVoice.classList.remove('bg-rose-600', 'text-white', 'border-rose-400', 'voice-recording-pulsing');
        this.btnVoice.classList.add('bg-slate-800', 'text-slate-300', 'border-slate-700');
        this.btnVoice.title = 'Falar comando de pista (Web Speech API)';
      }
    }

    if (this.indicator) {
      if (listening) {
        this.indicator.classList.remove('hidden');
        this.indicator.classList.add('flex');
      } else {
        this.indicator.classList.add('hidden');
        this.indicator.classList.remove('flex');
      }
    }
  }

  /**
   * Exibe mensagem acessivel de feedback temporario
   */
  showFeedback(message) {
    if (this.indicator) {
      const label = document.getElementById('voice-recording-label');
      if (label) {
        label.textContent = message;
      }
      this.indicator.classList.remove('hidden');
      this.indicator.classList.add('flex');
      setTimeout(() => {
        if (!this.isListening && this.indicator) {
          this.indicator.classList.add('hidden');
          this.indicator.classList.remove('flex');
          if (label) label.textContent = 'Ouvindo comando de pista...';
        }
      }, 3500);
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
