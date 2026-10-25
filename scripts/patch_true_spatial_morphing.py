import os
import re

BASE_DIR = "ia-banco-local"

# 1. Clean up web/css/aura.css: remove funnel styles, keep spatial layout transitions
css_path = os.path.join(BASE_DIR, "web", "css", "aura.css")
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

# Remove funnel section if present
funnel_marker = "/* =========================================================================\n   HOLOGRAPHIC FUNNEL ENTRANCE"
if funnel_marker in css:
    pos = css.find(funnel_marker)
    css = css[:pos].rstrip() + "\n"

spatial_css_clean = """
/* =========================================================================
   TRUE SPATIAL MORPHING (DYNAMIC ISLAND / APPLE VISION PRO)
   O proprio Companion Canvas se expande e recolhe a partir das coordenadas do botao
   ========================================================================= */
#view-console {
  transition: max-width 380ms cubic-bezier(0.16, 1, 0.3, 1);
}

#chat-stream-column {
  transition: width 380ms cubic-bezier(0.16, 1, 0.3, 1), flex 380ms cubic-bezier(0.16, 1, 0.3, 1);
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
"""

if "TRUE SPATIAL MORPHING (DYNAMIC ISLAND" not in css:
    css += "\n" + spatial_css_clean
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)
    print("1. web/css/aura.css updated with True Spatial Morphing styles")
else:
    print("1. web/css/aura.css already has Spatial Morphing styles")

# 2. Update web/js/aura-aux-panel.js with runSpatialMorphOpen and reverse morph on close
js_path = os.path.join(BASE_DIR, "web", "js", "aura-aux-panel.js")
with open(js_path, "r", encoding="utf-8") as f:
    js = f.read()

# Pattern to replace open() and any animateHolographicFunnel / animateSpatialMorph methods up to close()
pattern_open_block = r"  open\(artifactId = null, playSound = true[\s\S]*?(?=  /\*\*\r?\n   \* Alterna estado)"
match_open = re.search(pattern_open_block, js)
if not match_open:
    print("ERROR: could not find open block in aura-aux-panel.js")
    exit(1)

new_spatial_methods = """  open(artifactId = null, playSound = true, triggerElement = null) {
    if (artifactId) {
      this.activeArtifactId = artifactId;
    }

    this.isOpen = true;
    this.userDismissed = false;

    if (typeof document !== 'undefined') {
      this.previousFocusedElement = document.activeElement;

      // Identifica o botao gatilho de origem (card, acao ou header)
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

      // Se nenhum botao estiver focado, busca o cartao de resultado mais recente no chat
      if (!trigger) {
        trigger = document.querySelector('#chat-feed-container .aux-btn-view-panel:last-of-type') ||
                  document.querySelector('#chat-feed-container [data-action-id="act_default_canvas"]:last-of-type') ||
                  document.getElementById('btn-toggle-aux-panel');
      }

      this.lastTriggerElement = trigger;

      const consoleView = document.getElementById('view-console');
      const auxPanel = document.getElementById('aura-aux-panel');
      const btnToggle = document.getElementById('btn-toggle-aux-panel');
      const peekToast = document.getElementById('aux-artifact-peek-toast');
      const beacon = document.getElementById('aux-toggle-beacon');

      if (consoleView) {
        consoleView.classList.add('aux-panel-active');
        if (this.isExpanded) consoleView.classList.add('aux-expanded');
      }

      if (btnToggle) {
        btnToggle.setAttribute('aria-expanded', 'true');
        btnToggle.classList.add('bg-cyan-500/15', 'border-cyan-500/40', 'text-cyan-200');
      }

      if (peekToast) peekToast.classList.add('hidden');
      if (beacon) beacon.classList.add('hidden');

      this.renderActiveArtifact();

      if (auxPanel) {
        auxPanel.classList.remove('hidden');
        this.runSpatialMorphOpen(trigger, auxPanel);
      }

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
   * Spatial Morphing Real (Dynamic Island / Apple Vision Pro)
   * O proprio painel nasce nas coordenadas e dimensoes do botao clicado (FLIP)
   * e se expande organicamente no espaco atraves de transform 3D.
   */
  runSpatialMorphOpen(triggerEl, auxPanel) {
    if (!auxPanel || typeof document === 'undefined') return;

    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      auxPanel.style.transform = '';
      auxPanel.style.opacity = '1';
      return;
    }

    const btnRect = (triggerEl && typeof triggerEl.getBoundingClientRect === 'function')
      ? triggerEl.getBoundingClientRect()
      : null;

    if (!btnRect || btnRect.width === 0 || btnRect.height === 0) {
      auxPanel.style.transform = 'scale(0.95)';
      auxPanel.style.opacity = '0';
      requestAnimationFrame(() => {
        auxPanel.style.transition = 'transform 360ms cubic-bezier(0.16, 1, 0.3, 1), opacity 260ms ease-out';
        auxPanel.style.transform = 'scale(1)';
        auxPanel.style.opacity = '1';
        setTimeout(() => {
          auxPanel.style.transition = '';
          auxPanel.style.transform = '';
        }, 380);
      });
      return;
    }

    // Feedback visual tatil no botao de origem
    triggerEl.classList.remove('aux-btn-pulse-morph');
    void triggerEl.offsetWidth;
    triggerEl.classList.add('aux-btn-pulse-morph');

    auxPanel.style.transition = 'none';

    requestAnimationFrame(() => {
      const panelRect = auxPanel.getBoundingClientRect();
      if (!panelRect || panelRect.width === 0 || panelRect.height === 0) return;

      const deltaX = btnRect.left - panelRect.left;
      const deltaY = btnRect.top - panelRect.top;
      const scaleX = Math.max(0.05, Math.min(1, btnRect.width / panelRect.width));
      const scaleY = Math.max(0.02, Math.min(1, btnRect.height / panelRect.height));

      // Quadro 0: O painel comeca no mesmo local, tamanho e formato do botao
      auxPanel.style.transformOrigin = 'top left';
      auxPanel.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 0px) scale(${scaleX}, ${scaleY})`;
      auxPanel.style.borderRadius = '12px';
      auxPanel.style.opacity = '0.35';
      auxPanel.style.boxShadow = '0 0 25px rgba(6, 182, 212, 0.5)';

      const content = auxPanel.querySelector('.aux-panel-topbar, #aux-active-artifact-container');
      if (content) {
        content.style.transition = 'none';
        content.style.opacity = '0';
      }

      void auxPanel.offsetWidth;

      // Quadro 1: Expansao espacial continua em curva Apple Spring
      requestAnimationFrame(() => {
        auxPanel.style.transition = 'transform 380ms cubic-bezier(0.16, 1, 0.3, 1), opacity 280ms cubic-bezier(0.16, 1, 0.3, 1), border-radius 380ms ease-out, box-shadow 380ms ease-out';
        auxPanel.style.transform = 'translate3d(0px, 0px, 0px) scale(1, 1)';
        auxPanel.style.borderRadius = '16px';
        auxPanel.style.opacity = '1';
        auxPanel.style.boxShadow = '0 20px 50px -15px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255, 255, 255, 0.12)';

        if (content) {
          setTimeout(() => {
            content.style.transition = 'opacity 220ms ease-out, transform 280ms cubic-bezier(0.16, 1, 0.3, 1)';
            content.style.opacity = '1';
            content.style.transform = 'translateY(0px)';
          }, 120);
        }

        setTimeout(() => {
          auxPanel.style.transition = '';
          auxPanel.style.transform = '';
          auxPanel.style.transformOrigin = '';
          auxPanel.style.borderRadius = '';
          auxPanel.style.boxShadow = '';
          if (content) {
            content.style.transition = '';
            content.style.opacity = '';
            content.style.transform = '';
          }
        }, 400);
      });
    });
  }

  /**
   * Fecha o painel auxiliar com Spatial Morphing reverso em direcao ao botao de origem
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

      if (auxPanel && !auxPanel.classList.contains('hidden')) {
        const trigger = this.lastTriggerElement;
        const btnRect = (trigger && typeof trigger.getBoundingClientRect === 'function')
          ? trigger.getBoundingClientRect()
          : null;
        const panelRect = auxPanel.getBoundingClientRect();

        if (btnRect && panelRect && panelRect.width > 0) {
          const deltaX = btnRect.left - panelRect.left;
          const deltaY = btnRect.top - panelRect.top;
          const scaleX = Math.max(0.05, Math.min(1, btnRect.width / panelRect.width));
          const scaleY = Math.max(0.02, Math.min(1, btnRect.height / panelRect.height));

          auxPanel.style.transformOrigin = 'top left';
          auxPanel.style.transition = 'transform 260ms cubic-bezier(0.4, 0, 1, 1), opacity 200ms ease-out';
          auxPanel.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 0px) scale(${scaleX}, ${scaleY})`;
          auxPanel.style.opacity = '0';

          setTimeout(() => {
            auxPanel.classList.add('hidden');
            auxPanel.style.transition = '';
            auxPanel.style.transform = '';
            auxPanel.style.transformOrigin = '';
            auxPanel.style.opacity = '';
            if (consoleView) {
              consoleView.classList.remove('aux-panel-active', 'aux-expanded');
            }
          }, 260);
        } else {
          auxPanel.classList.add('hidden');
          if (consoleView) {
            consoleView.classList.remove('aux-panel-active', 'aux-expanded');
          }
        }
      } else if (consoleView) {
        consoleView.classList.remove('aux-panel-active', 'aux-expanded');
      }

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

js = js[:match_open.start()] + new_spatial_methods + js[match_open.end():]
with open(js_path, "w", encoding="utf-8") as f:
    f.write(js)

print("2. web/js/aura-aux-panel.js updated with True Spatial Morphing FLIP animation!")
