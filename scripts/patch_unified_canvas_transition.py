import os
import re

BASE_DIR = "ia-banco-local"

# 1. Update web/css/aura.css
css_path = os.path.join(BASE_DIR, "web", "css", "aura.css")
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

# Replace previous spatial morphing block with unified canvas animation
target_marker = "/* =========================================================================\n   SPATIAL MORPHING TRANSITION"
if target_marker in css:
    pos = css.find(target_marker)
    css = css[:pos].rstrip() + "\n"

unified_css = """
/* =========================================================================
   COMPANION CANVAS ENTRANCE & EXIT (SINCRONIZACAO FLUIDA APPLE-GRADE)
   Desdobramento nativo acelerado por hardware para todos os gatilhos
   ========================================================================= */
#view-console {
  transition: max-width 400ms cubic-bezier(0.16, 1, 0.3, 1);
}

#chat-stream-column {
  transition: width 400ms cubic-bezier(0.16, 1, 0.3, 1), flex 400ms cubic-bezier(0.16, 1, 0.3, 1);
}

.aux-btn-pulse-morph {
  animation: auxBtnPulseMorph 300ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes auxBtnPulseMorph {
  0% {
    transform: scale(1);
  }
  35% {
    transform: scale(0.93);
    box-shadow: 0 0 18px rgba(6, 182, 212, 0.55);
  }
  100% {
    transform: scale(1);
    box-shadow: none;
  }
}

.aux-panel-entrance {
  animation: auxCanvasEntrance 440ms cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
  will-change: transform, opacity, filter, box-shadow;
  transform-origin: right center;
}

@keyframes auxCanvasEntrance {
  0% {
    opacity: 0;
    transform: translateX(36px) scale(0.97);
    filter: blur(8px);
    box-shadow: 0 0 0 rgba(6, 182, 212, 0);
  }
  50% {
    opacity: 0.95;
    filter: blur(1px);
    box-shadow: 0 12px 42px -8px rgba(6, 182, 212, 0.35), 0 0 25px rgba(124, 58, 237, 0.22);
  }
  100% {
    opacity: 1;
    transform: translateX(0) scale(1);
    filter: blur(0);
    box-shadow: 0 20px 50px -15px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255, 255, 255, 0.12);
  }
}

.aux-panel-exit {
  animation: auxCanvasExit 220ms cubic-bezier(0.4, 0, 1, 1) forwards !important;
  will-change: transform, opacity, filter;
  pointer-events: none;
}

@keyframes auxCanvasExit {
  0% {
    opacity: 1;
    transform: translateX(0) scale(1);
    filter: blur(0);
  }
  100% {
    opacity: 0;
    transform: translateX(32px) scale(0.98);
    filter: blur(4px);
  }
}

.aux-panel-entrance #aux-active-artifact-container {
  animation: auxContentCascade 480ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes auxContentCascade {
  0% {
    opacity: 0;
    transform: translateY(14px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 767px) {
  .aux-panel-entrance {
    animation: auxCanvasMobileEntrance 380ms cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
    transform-origin: bottom center;
  }
  @keyframes auxCanvasMobileEntrance {
    0% {
      opacity: 0;
      transform: translateY(100%);
    }
    100% {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .aux-panel-exit {
    animation: auxCanvasMobileExit 220ms cubic-bezier(0.4, 0, 1, 1) forwards !important;
  }
  @keyframes auxCanvasMobileExit {
    0% {
      opacity: 1;
      transform: translateY(0);
    }
    100% {
      opacity: 0;
      transform: translateY(100%);
    }
  }
}
"""

css += "\n" + unified_css
with open(css_path, "w", encoding="utf-8") as f:
    f.write(css)

print("1. web/css/aura.css updated with unified entrance & exit transitions!")

# 2. Update web/js/aura-aux-panel.js
js_path = os.path.join(BASE_DIR, "web", "js", "aura-aux-panel.js")
with open(js_path, "r", encoding="utf-8") as f:
    js = f.read()

# Replace open() method and remove animateSpatialMorph
open_pattern = r"  open\(artifactId = null, playSound = true[\s\S]*?(?=  /\*\*\r?\n   \* Alterna estado)"
match_open = re.search(open_pattern, js)
if not match_open:
    print("ERROR: could not find open block in aura-aux-panel.js")
    exit(1)

new_open_and_close = """  open(artifactId = null, playSound = true, triggerElement = null) {
    if (artifactId) {
      this.activeArtifactId = artifactId;
    }

    this.isOpen = true;
    this.userDismissed = false;

    if (typeof document !== 'undefined') {
      this.previousFocusedElement = document.activeElement;

      // Identifica qualquer botao gatilho acionado (card, acao ou header)
      let trigger = triggerElement;
      if (!trigger && document.activeElement) {
        const el = document.activeElement;
        if (
          el.id === 'btn-toggle-aux-panel' ||
          (typeof el.closest === 'function' && el.closest('#btn-toggle-aux-panel')) ||
          el.classList?.contains('aux-btn-view-panel') ||
          el.classList?.contains('aux-btn-view-chat') ||
          el.getAttribute?.('data-action-id') === 'act_default_canvas'
        ) {
          trigger = el;
        }
      }

      // Feedback tatil suave no botao gatilho
      if (trigger) {
        trigger.classList.remove('aux-btn-pulse-morph');
        void trigger.offsetWidth;
        trigger.classList.add('aux-btn-pulse-morph');
      }

      const consoleView = document.getElementById('view-console');
      const auxPanel = document.getElementById('aura-aux-panel');
      const btnToggle = document.getElementById('btn-toggle-aux-panel');
      const peekToast = document.getElementById('aux-artifact-peek-toast');
      const beacon = document.getElementById('aux-toggle-beacon');

      if (consoleView) {
        consoleView.classList.add('aux-panel-active');
        if (this.isExpanded) consoleView.classList.add('aux-expanded');
      }

      if (auxPanel) {
        auxPanel.classList.remove('hidden', 'aux-panel-exit');
        auxPanel.classList.remove('aux-panel-entrance');
        void auxPanel.offsetWidth; // Forca reflow para reiniciar a animacao com precisao
        auxPanel.classList.add('aux-panel-entrance');
      }

      if (btnToggle) {
        btnToggle.setAttribute('aria-expanded', 'true');
        btnToggle.classList.add('bg-cyan-500/15', 'border-cyan-500/40', 'text-cyan-200');
      }

      if (peekToast) peekToast.classList.add('hidden');
      if (beacon) beacon.classList.add('hidden');

      this.renderActiveArtifact();

      // Rola para a mensagem associada no chat
      const activeArt = this.getActiveArtifact();
      if (activeArt && activeArt.containerId) {
        const msgEl = document.getElementById(activeArt.containerId);
        if (msgEl) {
          msgEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    }

    if (playSound && typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(680, 0.06);
    }
  }

  /**
   * Fecha o painel auxiliar e devolve o layout ao centro confortavel
   */
  close(playSound = true) {
    this.isOpen = false;
    this.userDismissed = true;

    if (typeof document !== 'undefined') {
      const consoleView = document.getElementById('view-console');
      const auxPanel = document.getElementById('aura-aux-panel');
      const btnToggle = document.getElementById('btn-toggle-aux-panel');

      if (btnToggle) {
        btnToggle.setAttribute('aria-expanded', 'false');
        btnToggle.classList.remove('bg-cyan-500/15', 'border-cyan-500/40', 'text-cyan-200');
      }

      if (auxPanel) {
        auxPanel.classList.remove('aux-panel-entrance');
        auxPanel.classList.add('aux-panel-exit');
        setTimeout(() => {
          auxPanel.classList.add('hidden');
          auxPanel.classList.remove('aux-panel-exit');
          if (consoleView) {
            consoleView.classList.remove('aux-panel-active', 'aux-expanded');
          }
        }, 220);
      } else if (consoleView) {
        consoleView.classList.remove('aux-panel-active', 'aux-expanded');
      }

      // Restaura foco ao gatilho que abriu ou ao input de chat (WCAG 2.1 AA)
      if (this.previousFocusedElement && typeof this.previousFocusedElement.focus === 'function') {
        this.previousFocusedElement.focus({ preventScroll: true });
      } else {
        const chatInput = document.getElementById('chat-input-text');
        if (chatInput && typeof chatInput.focus === 'function') {
          chatInput.focus({ preventScroll: true });
        }
      }
    }

    if (playSound && typeof window !== 'undefined' && window.auraAudio && typeof window.auraAudio.playChime === 'function') {
      window.auraAudio.playChime(520, 0.05);
    }
  }

"""

js = js[:match_open.start()] + new_open_and_close + js[match_open.end():]
with open(js_path, "w", encoding="utf-8") as f:
    f.write(js)

print("2. web/js/aura-aux-panel.js updated cleanly without fake overlay capsules!")
