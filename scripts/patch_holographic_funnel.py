import os
import re

BASE_DIR = "ia-banco-local"

# 1. Update web/css/aura.css with Holographic Funnel animations
css_path = os.path.join(BASE_DIR, "web", "css", "aura.css")
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

funnel_css = """
/* =========================================================================
   HOLOGRAPHIC FUNNEL ENTRANCE (PROJECAO ESPACIAL EM FUNIL A PARTIR DO BOTAO)
   Visual futurista de feixe conico conectando o botao de origem ao Canvas
   ========================================================================= */
.aura-funnel-mesh {
  animation: funnelMeshExpand 440ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  will-change: opacity, transform;
}

@keyframes funnelMeshExpand {
  0% {
    opacity: 0;
    transform: scaleX(0.08);
    transform-origin: left center;
  }
  35% {
    opacity: 0.85;
  }
  80% {
    opacity: 0.65;
  }
  100% {
    opacity: 0;
    transform: scaleX(1);
    transform-origin: left center;
  }
}

.aura-funnel-ray {
  animation: funnelRayShoot 440ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  will-change: stroke-dashoffset, opacity;
}

@keyframes funnelRayShoot {
  0% {
    opacity: 0;
    stroke-dasharray: 900;
    stroke-dashoffset: 900;
  }
  25% {
    opacity: 1;
  }
  85% {
    opacity: 0.9;
    stroke-dashoffset: 0;
  }
  100% {
    opacity: 0;
    stroke-dashoffset: 0;
  }
}

.aux-panel-funnel-bloom {
  animation: auxPanelFunnelBloom 440ms cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
  will-change: transform, opacity, filter, box-shadow;
}

@keyframes auxPanelFunnelBloom {
  0% {
    opacity: 0;
    transform: scale(0.92) translateX(28px);
    filter: blur(8px);
    box-shadow: 0 0 0 rgba(6, 182, 212, 0);
  }
  40% {
    opacity: 0.95;
    filter: blur(1.5px);
    box-shadow: 0 0 45px rgba(6, 182, 212, 0.4), 0 0 25px rgba(124, 58, 237, 0.25);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateX(0);
    filter: blur(0);
    box-shadow: 0 20px 50px -15px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255, 255, 255, 0.12);
  }
}
"""

if ".aura-funnel-mesh" not in css:
    css += "\n" + funnel_css
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)
    print("1. web/css/aura.css updated with funnel animations")
else:
    print("1. web/css/aura.css already has funnel animations")

# 2. Update web/js/aura-aux-panel.js with animateHolographicFunnel
js_path = os.path.join(BASE_DIR, "web", "js", "aura-aux-panel.js")
with open(js_path, "r", encoding="utf-8") as f:
    js = f.read()

# Replace open() method and insert animateHolographicFunnel
new_open_and_funnel = """  open(artifactId = null, playSound = true, triggerElement = null) {
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

      // Se nenhum botao estiver focado, busca o cartao de resultado mais recente no chat
      if (!trigger) {
        trigger = document.querySelector('#chat-feed-container .aux-btn-view-panel:last-of-type') ||
                  document.querySelector('#chat-feed-container [data-action-id="act_default_canvas"]:last-of-type') ||
                  document.getElementById('btn-toggle-aux-panel');
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
        if (trigger && typeof trigger.getBoundingClientRect === 'function') {
          this.animateHolographicFunnel(trigger, auxPanel);
        } else {
          auxPanel.classList.remove('aux-panel-entrance');
          void auxPanel.offsetWidth;
          auxPanel.classList.add('aux-panel-entrance');
        }
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
   * Animacao Holografica em Funil (Holographic Funnel)
   * Projeta visualmente um feixe conico de luz em curva de Bezier
   * saindo das coordenadas do botao gatilho e desdobrando o Companion Canvas.
   */
  animateHolographicFunnel(triggerEl, auxPanel) {
    if (!triggerEl || !auxPanel || typeof document === 'undefined') return;

    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      auxPanel.classList.add('aux-panel-entrance');
      return;
    }

    const btnRect = triggerEl.getBoundingClientRect();
    if (!btnRect || btnRect.width === 0 || btnRect.height === 0) {
      auxPanel.classList.add('aux-panel-entrance');
      return;
    }

    // Feedback visual tatil no botao de origem
    triggerEl.classList.remove('aux-btn-pulse-morph');
    void triggerEl.offsetWidth;
    triggerEl.classList.add('aux-btn-pulse-morph');

    // Remove qualquer overlay residual anterior
    document.querySelectorAll('.aura-funnel-overlay').forEach(el => el.remove());

    // Cria overlay SVG na viewport inteira
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'aura-funnel-overlay fixed inset-0 w-full h-full pointer-events-none z-50');
    svg.style.position = 'fixed';
    svg.style.inset = '0';
    svg.style.width = '100vw';
    svg.style.height = '100vh';
    svg.style.pointerEvents = 'none';
    svg.style.zIndex = '9998';

    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
      <linearGradient id="auraFunnelGrad" x1="0%" y1="50%" x2="100%" y2="50%">
        <stop offset="0%" stop-color="#06b6d4" stop-opacity="0.80"/>
        <stop offset="40%" stop-color="#38bdf8" stop-opacity="0.50"/>
        <stop offset="75%" stop-color="#818cf8" stop-opacity="0.30"/>
        <stop offset="100%" stop-color="#06b6d4" stop-opacity="0.10"/>
      </linearGradient>
      <linearGradient id="auraBeamGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#22d3ee" stop-opacity="1"/>
        <stop offset="50%" stop-color="#c084fc" stop-opacity="0.85"/>
        <stop offset="100%" stop-color="#06b6d4" stop-opacity="0.45"/>
      </linearGradient>
      <filter id="auraFunnelGlow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="5" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    `;
    svg.appendChild(defs);

    requestAnimationFrame(() => {
      const panelRect = auxPanel.getBoundingClientRect();
      if (!panelRect || panelRect.width === 0 || panelRect.height === 0) {
        auxPanel.classList.add('aux-panel-entrance');
        return;
      }

      const isMobile = window.innerWidth < 768;
      let pathD = '';
      let topRayD = '';
      let bottomRayD = '';

      if (isMobile) {
        const bx1 = btnRect.left;
        const by1 = btnRect.top;
        const bx2 = btnRect.right;
        const by2 = btnRect.top;
        const px1 = 0;
        const py1 = panelRect.top;
        const px2 = window.innerWidth;
        const py2 = panelRect.top;
        const dy = Math.max(20, (py1 - by1) * 0.5);

        pathD = `M ${bx1},${by1} C ${bx1},${by1 + dy} ${px1},${py1 - dy} ${px1},${py1} L ${px2},${py2} C ${px2},${py2 - dy} ${bx2},${by2 + dy} ${bx2},${by2} Z`;
        topRayD = `M ${bx1},${by1} C ${bx1},${by1 + dy} ${px1},${py1 - dy} ${px1},${py1}`;
        bottomRayD = `M ${bx2},${by2} C ${bx2},${by2 + dy} ${px2},${py2 - dy} ${px2},${py2}`;
      } else {
        const bx1 = btnRect.right;
        const by1 = btnRect.top;
        const bx2 = btnRect.right;
        const by2 = btnRect.bottom;
        const px1 = panelRect.left;
        const py1 = panelRect.top;
        const px2 = panelRect.left;
        const py2 = panelRect.bottom;
        const dx = Math.max(30, (px1 - bx1) * 0.52);

        pathD = `M ${bx1},${by1} C ${bx1 + dx},${by1} ${px1 - dx},${py1} ${px1},${py1} L ${px2},${py2} C ${px1 - dx},${py2} ${bx2 + dx},${by2} ${bx2},${by2} Z`;
        topRayD = `M ${bx1},${by1} C ${bx1 + dx},${by1} ${px1 - dx},${py1} ${px1},${py1}`;
        bottomRayD = `M ${bx2},${by2} C ${bx2 + dx},${by2} ${px2 - dx},${py2} ${px2},${py2}`;
      }

      const funnelPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      funnelPath.setAttribute('d', pathD);
      funnelPath.setAttribute('fill', 'url(#auraFunnelGrad)');
      funnelPath.setAttribute('class', 'aura-funnel-mesh');

      const topRay = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      topRay.setAttribute('d', topRayD);
      topRay.setAttribute('fill', 'none');
      topRay.setAttribute('stroke', 'url(#auraBeamGrad)');
      topRay.setAttribute('stroke-width', '2.5');
      topRay.setAttribute('filter', 'url(#auraFunnelGlow)');
      topRay.setAttribute('class', 'aura-funnel-ray');

      const bottomRay = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      bottomRay.setAttribute('d', bottomRayD);
      bottomRay.setAttribute('fill', 'none');
      bottomRay.setAttribute('stroke', 'url(#auraBeamGrad)');
      bottomRay.setAttribute('stroke-width', '2.5');
      bottomRay.setAttribute('filter', 'url(#auraFunnelGlow)');
      bottomRay.setAttribute('class', 'aura-funnel-ray');

      svg.appendChild(funnelPath);
      svg.appendChild(topRay);
      svg.appendChild(bottomRay);
      document.body.appendChild(svg);

      const panelOriginY = Math.max(10, Math.min(panelRect.height - 10, btnRect.top - panelRect.top + btnRect.height / 2));
      auxPanel.style.transformOrigin = `0px ${panelOriginY}px`;
      auxPanel.classList.remove('hidden', 'aux-panel-exit');
      auxPanel.classList.remove('aux-panel-funnel-bloom');
      void auxPanel.offsetWidth;
      auxPanel.classList.add('aux-panel-funnel-bloom');

      setTimeout(() => {
        svg.style.transition = 'opacity 180ms ease-out';
        svg.style.opacity = '0';
        setTimeout(() => {
          if (svg.parentNode) svg.parentNode.removeChild(svg);
          auxPanel.classList.remove('aux-panel-funnel-bloom');
          auxPanel.style.transformOrigin = '';
        }, 180);
      }, 420);
    });
  }
"""

open_pattern = r"  open\(artifactId = null, playSound = true[\s\S]*?(?=  /\*\*\r?\n   \* Fecha o painel)"
match_open = re.search(open_pattern, js)
if not match_open:
    print("ERROR: could not find open block in aura-aux-panel.js")
    exit(1)

js = js[:match_open.start()] + new_open_and_funnel + js[match_open.end():]
with open(js_path, "w", encoding="utf-8") as f:
    f.write(js)

print("2. web/js/aura-aux-panel.js updated with animateHolographicFunnel!")
