"""
Script de implementacao do Spatial Morphing (Abordagem 1 - Dynamic Island / Apple Vision Pro)
Expansao continua fluida a partir do botao 'Ver no Painel' em direcao ao Companion Canvas.
Regra inegociavel: ZERO TRAVESSOES.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Atualizar aura.css com as classes de Spatial Morphing
css_path = os.path.join(BASE_DIR, "web", "css", "aura.css")
with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()

spatial_css = """
/* =========================================================================
   SPATIAL MORPHING TRANSITION (ABORDAGEM 1: DYNAMIC ISLAND / APPLE VISION PRO)
   Membrana liquida de vidro de alta fidelidade que se expande a partir do botao
   ========================================================================= */
.aura-spatial-morph-capsule {
  position: fixed;
  box-sizing: border-box;
  pointer-events: none;
  z-index: 9999;
  transform-origin: center center;
  will-change: left, top, width, height, opacity, transform, border-radius, box-shadow;
  transition: 
    left 340ms cubic-bezier(0.16, 1, 0.3, 1),
    top 340ms cubic-bezier(0.16, 1, 0.3, 1),
    width 340ms cubic-bezier(0.16, 1, 0.3, 1),
    height 340ms cubic-bezier(0.16, 1, 0.3, 1),
    border-radius 340ms cubic-bezier(0.16, 1, 0.3, 1),
    background 340ms cubic-bezier(0.16, 1, 0.3, 1),
    border-color 340ms cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 340ms cubic-bezier(0.16, 1, 0.3, 1),
    opacity 160ms ease-out;
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

.aux-panel-morphing-in {
  animation: auxPanelMorphSettle 360ms cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
  will-change: opacity, transform, filter;
}

@keyframes auxPanelMorphSettle {
  0% {
    opacity: 0;
    filter: blur(8px);
    transform: scale(0.98) translateX(12px);
  }
  45% {
    opacity: 0.8;
    filter: blur(2px);
  }
  100% {
    opacity: 1;
    filter: blur(0);
    transform: scale(1) translateX(0);
  }
}
"""

if ".aura-spatial-morph-capsule" not in css_content:
    css_content += spatial_css
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_content)
    print("1. aura.css atualizado com sucesso!")
else:
    print("1. aura.css ja contem classes de morphing.")

# 2. Atualizar aura-aux-panel.js com o metodo animateSpatialMorph e suporte a triggerElement em open()
aux_path = os.path.join(BASE_DIR, "web", "js", "aura-aux-panel.js")
with open(aux_path, "r", encoding="utf-8") as f:
    aux_content = f.read()

old_open_decl = "  open(artifactId = null, playSound = true) {"
new_open_decl = "  open(artifactId = null, playSound = true, triggerElement = null) {"

old_open_body = """      if (auxPanel) {
        auxPanel.classList.remove('hidden');
        auxPanel.classList.add('animate-fade-in');
      }"""

new_open_body = """      // Detecta elemento de clique para orquestracao Spatial Morphing
      let trigger = triggerElement;
      if (!trigger && typeof document !== 'undefined' && document.activeElement) {
        const el = document.activeElement;
        if (
          el.classList?.contains('aux-btn-view-panel') ||
          el.classList?.contains('aux-btn-view-chat') ||
          el.getAttribute?.('data-action-id') === 'act_default_canvas'
        ) {
          trigger = el;
        }
      }

      if (auxPanel) {
        auxPanel.classList.remove('hidden');
        if (trigger) {
          this.animateSpatialMorph(trigger, auxPanel);
        } else {
          auxPanel.classList.add('animate-fade-in');
        }
      }"""

if old_open_decl in aux_content:
    aux_content = aux_content.replace(old_open_decl, new_open_decl, 1)

if old_open_body in aux_content:
    aux_content = aux_content.replace(old_open_body, new_open_body, 1)

spatial_morph_method = """
  /**
   * Transicao de Expansao Espacial Continua (Spatial Morphing: Abordagem 1)
   * Desdobra organicamente o botao clicado em direcao ao Companion Canvas
   * com fisica de mola (Apple Spring Curve) e acabamento Precision Glass.
   */
  animateSpatialMorph(triggerEl, auxPanel) {
    if (!triggerEl || !auxPanel || typeof document === 'undefined') return;

    // Respeita acessibilidade de reducao de movimento
    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      auxPanel.classList.add('animate-fade-in');
      return;
    }

    const sourceRect = triggerEl.getBoundingClientRect();
    if (!sourceRect || sourceRect.width === 0 || sourceRect.height === 0) {
      auxPanel.classList.add('animate-fade-in');
      return;
    }

    // Feedback visual tatil no botao de origem
    triggerEl.classList.remove('aux-btn-pulse-morph');
    void triggerEl.offsetWidth;
    triggerEl.classList.add('aux-btn-pulse-morph');

    // Remove qualquer capsula residual anterior
    document.querySelectorAll('.aura-spatial-morph-capsule').forEach(el => el.remove());

    // Cria a capsula efemera na coordenada exata do botao de clique
    const capsule = document.createElement('div');
    capsule.className = 'aura-spatial-morph-capsule';
    capsule.style.left = `${sourceRect.left}px`;
    capsule.style.top = `${sourceRect.top}px`;
    capsule.style.width = `${sourceRect.width}px`;
    capsule.style.height = `${sourceRect.height}px`;
    capsule.style.borderRadius = `${window.getComputedStyle(triggerEl).borderRadius || '12px'}`;
    capsule.style.background = 'linear-gradient(135deg, rgba(6, 182, 212, 0.45), rgba(124, 58, 237, 0.4))';
    capsule.style.border = '1px solid rgba(6, 182, 212, 0.7)';
    capsule.style.boxShadow = '0 0 25px rgba(6, 182, 212, 0.55), inset 0 0 14px rgba(255, 255, 255, 0.25)';
    capsule.style.backdropFilter = 'blur(12px)';
    capsule.style.webkitBackdropFilter = 'blur(12px)';
    capsule.style.opacity = '1';

    document.body.appendChild(capsule);

    // Configura o painel real para transicao suave
    auxPanel.classList.remove('animate-fade-in');
    auxPanel.classList.add('aux-panel-morphing-in');

    // Executa a expansao espacial em direcao ao Canvas no proximo quadro
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const targetRect = auxPanel.getBoundingClientRect();
        if (targetRect && targetRect.width > 0 && targetRect.height > 0) {
          capsule.style.left = `${targetRect.left}px`;
          capsule.style.top = `${targetRect.top}px`;
          capsule.style.width = `${targetRect.width}px`;
          capsule.style.height = `${targetRect.height}px`;
          capsule.style.borderRadius = '16px';
          capsule.style.border = '1px solid rgba(6, 182, 212, 0.35)';
          capsule.style.background = 'rgba(12, 18, 30, 0.88)';
          capsule.style.boxShadow = '0 12px 44px rgba(0, 0, 0, 0.65), 0 0 35px rgba(6, 182, 212, 0.25)';
        }

        setTimeout(() => {
          capsule.style.opacity = '0';
          setTimeout(() => {
            if (capsule.parentNode) capsule.parentNode.removeChild(capsule);
            auxPanel.classList.remove('aux-panel-morphing-in');
          }, 160);
        }, 340);
      });
    });
  }
"""

if "animateSpatialMorph(" not in aux_content:
    # Inserir antes de close()
    pos_close = aux_content.find("  close(playSound = true) {")
    if pos_close != -1:
        aux_content = aux_content[:pos_close] + spatial_morph_method + "\n" + aux_content[pos_close:]
        with open(aux_path, "w", encoding="utf-8") as f:
            f.write(aux_content)
        print("2. aura-aux-panel.js atualizado com sucesso!")
    else:
        print("ERRO: metodo close() nao encontrado em aura-aux-panel.js")
        sys.exit(1)
else:
    print("2. aura-aux-panel.js ja contem animateSpatialMorph.")

# 3. Atualizar aura-chat.js para passar 'this' em open('${artifactId}')
chat_path = os.path.join(BASE_DIR, "web", "js", "aura-chat.js")
with open(chat_path, "r", encoding="utf-8") as f:
    chat_content = f.read()

old_chat_call = "window.auraAuxPanel.open('${artifactId}')"
new_chat_call = "window.auraAuxPanel.open('${artifactId}', true, this)"

if old_chat_call in chat_content:
    chat_content = chat_content.replace(old_chat_call, new_chat_call)
    with open(chat_path, "w", encoding="utf-8") as f:
        f.write(chat_content)
    print("3. aura-chat.js atualizado com sucesso!")
else:
    print("3. aura-chat.js ja possui chamada com triggerElement.")

# 4. Atualizar aura-genui-widgets.js para passar 'btnElement' em open()
widgets_path = os.path.join(BASE_DIR, "web", "js", "aura-genui-widgets.js")
with open(widgets_path, "r", encoding="utf-8") as f:
    widgets_content = f.read()

old_widgets_call = "window.auraAuxPanel.open('art_genui_' + this.toolCallId);"
new_widgets_call = "window.auraAuxPanel.open('art_genui_' + this.toolCallId, true, btnElement);"

if old_widgets_call in widgets_content:
    widgets_content = widgets_content.replace(old_widgets_call, new_widgets_call)
    with open(widgets_path, "w", encoding="utf-8") as f:
        f.write(widgets_content)
    print("4. aura-genui-widgets.js atualizado com sucesso!")
else:
    print("4. aura-genui-widgets.js ja possui chamada com btnElement.")

print("CONCLUIDO: Todas as 4 atualizacoes da Abordagem 1 (Spatial Morphing) foram aplicadas.")
