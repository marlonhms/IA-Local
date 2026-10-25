"""
Script de orquestracao UI/UX de streaming para AURA:
1. Texto primeiro, card emergindo com animacao WOW apos o chat.
2. Inversao de ordem no DOM: text antes de tool-card.
3. handleUISkeleton nao polui tela antes do streaming.
4. handleDoneReconciliation agenda montagem suave com micro-pausa de 160ms.
5. Suporte a options.animated em handleUIComplete e renderCompanionPortalCard.
"""

import sys
import re

FILE_PATH = "web/js/aura-chat.js"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. createAuraMessageBubble: swap tool-card and text
old_bubble = """        <!-- Card de Resultado da Ferramenta Estruturada (se houver) -->
        <div id="${containerId}-tool-card" class="hidden w-full"></div>

        <!-- Texto em Streaming -->
        <div id="${containerId}-text" class="prose-aura typing-cursor">
          <span class="text-slate-400 text-xs font-sans">Processando consulta analítica...</span>
        </div>"""

new_bubble = """        <!-- Texto em Streaming -->
        <div id="${containerId}-text" class="prose-aura typing-cursor">
          <span class="text-slate-400 text-xs font-sans">Processando consulta analítica...</span>
        </div>

        <!-- Card de Resultado da Ferramenta Estruturada (emerge com efeito WOW apos o texto) -->
        <div id="${containerId}-tool-card" class="hidden w-full pt-2"></div>"""

if old_bubble not in content:
    print("ERROR: old_bubble not found in aura-chat.js")
    sys.exit(1)

content = content.replace(old_bubble, new_bubble, 1)

# 2. handleUISkeleton: clean and non-intrusive (keep timers, update cognitive step, do not force-reveal toolCard)
pattern_skeleton = r"  handleUISkeleton\(containerId, skeletonData\) \{[\s\S]*?this\.scrollToBottom\(\);\s*\}"
match_skele = re.search(pattern_skeleton, content)
if not match_skele:
    print("ERROR: handleUISkeleton pattern not matched")
    sys.exit(1)

new_skeleton_code = """  handleUISkeleton(containerId, skeletonData) {
    if (!skeletonData || typeof document === 'undefined') return;

    // Feature Flag F9-01: Se GenUI desativado no cliente, ignora skeleton e faz fallback para cards legados
    if (typeof window !== 'undefined' && window.AuraGenUI && typeof window.AuraGenUI.isEnabled === 'function') {
      if (!window.AuraGenUI.isEnabled()) return;
    }

    const toolCallId = skeletonData.tool_call_id || ('call_' + Date.now());

    // Telemetria SRE (F9-02): Medir inicio da hidratacao (skeleton) com performance.now()
    this._skeletonTimers = this._skeletonTimers || {};
    this._skeletonTimers[toolCallId] = (typeof performance !== 'undefined' && typeof performance.now === 'function')
      ? performance.now()
      : Date.now();

    const rawTitle = skeletonData.title || 'Analisando indicadores executivos...';
    // Atualiza chip cognitivo no header da mensagem sem abrir card prematuro antes do texto
    this.updateCognitiveStep(containerId, rawTitle, 'cyan');
  }"""

content = content[:match_skele.start()] + new_skeleton_code + content[match_skele.end():]

# 3. sendMessage streaming state variables and handleDoneReconciliation
old_streaming_vars = """    // Contexto de streaming
    let fullResponseText = '';
    let currentIntent = null;
    let currentToolResult = null;
    let currentToolName = null;
    let uiCompleteReceived = false;
    let lastGenUIEnvelope = null;
    let telemetryData = null;
    let hasStreamError = false;"""

new_streaming_vars = """    // Contexto de streaming
    let fullResponseText = '';
    let currentIntent = null;
    let currentToolResult = null;
    let currentToolName = null;
    let uiCompleteReceived = false;
    let lastGenUIEnvelope = null;
    let pendingGenUIEnvelope = null;
    let pendingFallbackTool = null;
    let telemetryData = null;
    let hasStreamError = false;"""

if old_streaming_vars not in content:
    print("ERROR: old_streaming_vars not found")
    sys.exit(1)

content = content.replace(old_streaming_vars, new_streaming_vars, 1)

# 4. handleDoneReconciliation: schedule mount with WOW animation
pattern_done = r"    const handleDoneReconciliation = \(\) => \{[\s\S]*?this\.expireStaleWidgets\(\);\s*\};"
match_done = re.search(pattern_done, content)
if not match_done:
    print("ERROR: handleDoneReconciliation pattern not matched")
    sys.exit(1)

new_done_code = """    const handleDoneReconciliation = () => {
      if (hasStreamError) return;
      this.updateAuraText(messageContainerId, fullResponseText, false);
      this.finalizeCognitiveStep(messageContainerId, true);

      const scheduleMount = (callback) => {
        // Micro-pausa de 160ms para ritmo de leitura executiva: o texto fixa primeiro, e o card emerge depois com efeito WOW
        setTimeout(() => {
          this.cleanupSkeletonSlots(messageContainerId);
          callback();
          this.scrollToBottom();
        }, 160);
      };

      if (pendingGenUIEnvelope) {
        const envToMount = pendingGenUIEnvelope;
        pendingGenUIEnvelope = null;
        scheduleMount(() => {
          this.handleUIComplete(messageContainerId, envToMount, { animated: true });
        });
      } else if (pendingFallbackTool) {
        const toolInfo = pendingFallbackTool;
        pendingFallbackTool = null;
        scheduleMount(() => {
          this.updateToolResultCard(messageContainerId, toolInfo.name, toolInfo.result, true, { animated: true });
        });
      } else if (!uiCompleteReceived && currentToolResult) {
        // Fallback gracioso: o backend executou a ferramenta mas nao emitiu GenUIEnvelope
        const tName = currentToolName || 'ferramenta';
        const tResult = currentToolResult;
        scheduleMount(() => {
          this.updateToolResultCard(messageContainerId, tName, tResult, true, { animated: true });
        });
      } else {
        this.cleanupSkeletonSlots(messageContainerId);
      }

      if (typeof window !== 'undefined' && window.AuraStorage) {
        window.AuraStorage.saveMessage(this.sessionId, {
          id: messageContainerId,
          role: 'assistant',
          text: fullResponseText,
          intent: currentIntent,
          genuiEnvelope: lastGenUIEnvelope,
          toolName: currentToolName,
          toolResult: currentToolResult,
          telemetry: telemetryData,
          timestamp: Date.now()
        });
      }
      this.setStreamingState(false);
      this.scrollToBottom(false);
      this.expireStaleWidgets();
    };"""

content = content[:match_done.start()] + new_done_code + content[match_done.end():]

# 5. onUIComplete in streamChat: hold pendingGenUIEnvelope
old_on_ui_complete = """        onUIComplete: (envelopeData) => {
          if (typeof window !== 'undefined' && window.AuraGenUI && typeof window.AuraGenUI.isEnabled === 'function') {
            if (!window.AuraGenUI.isEnabled()) {
              // GenUI desativado no cliente: fallback transparente para DecisionCards legados
              if (currentToolResult) {
                this.updateToolResultCard(messageContainerId, currentToolName || envelopeData.component_name || 'ferramenta', currentToolResult, true);
              }
              return;
            }
          }
          uiCompleteReceived = true;
          lastGenUIEnvelope = envelopeData;
          this.handleUIComplete(messageContainerId, envelopeData);
        },"""

new_on_ui_complete = """        onUIComplete: (envelopeData) => {
          if (typeof window !== 'undefined' && window.AuraGenUI && typeof window.AuraGenUI.isEnabled === 'function') {
            if (!window.AuraGenUI.isEnabled()) {
              // GenUI desativado no cliente: fallback transparente para DecisionCards legados
              if (currentToolResult) {
                pendingFallbackTool = {
                  name: currentToolName || envelopeData.component_name || 'ferramenta',
                  result: currentToolResult
                };
              }
              return;
            }
          }
          uiCompleteReceived = true;
          lastGenUIEnvelope = envelopeData;
          if (this.isStreaming) {
            // Em streaming ativo: aguarda conclusao do texto para emergir com efeito WOW
            pendingGenUIEnvelope = envelopeData;
          } else {
            // Texto ja concluiu: emerge imediatamente com animacao WOW
            setTimeout(() => {
              this.cleanupSkeletonSlots(messageContainerId);
              this.handleUIComplete(messageContainerId, envelopeData, { animated: true });
              this.scrollToBottom();
            }, 120);
          }
        },"""

if old_on_ui_complete not in content:
    print("ERROR: old_on_ui_complete not found")
    sys.exit(1)

content = content.replace(old_on_ui_complete, new_on_ui_complete, 1)

# 6. onChunk tool_result: do not prematurely display card
old_tool_result = """          else if (type === 'tool_result') {
            const toolName = chunk.data?.tool_name || chunk.data?.intent || chunk.tool_name || chunk.intent || 'ferramenta';
            currentToolName = toolName;
            currentToolResult = chunk.data?.result || chunk.data || {};
            this.updateToolResultCard(messageContainerId, toolName, currentToolResult);
            this.updateCognitiveStep(messageContainerId, 'Confrontando dados e regras de negócio...', 'purple');
          }"""

new_tool_result = """          else if (type === 'tool_result') {
            const toolName = chunk.data?.tool_name || chunk.data?.intent || chunk.tool_name || chunk.intent || 'ferramenta';
            currentToolName = toolName;
            currentToolResult = chunk.data?.result || chunk.data || {};
            // Registra os dados da ferramenta sem abrir card prematuro antes do texto
            this.updateCognitiveStep(messageContainerId, 'Confrontando dados e regras de negócio...', 'purple');
          }"""

if old_tool_result not in content:
    print("ERROR: old_tool_result not found")
    sys.exit(1)

content = content.replace(old_tool_result, new_tool_result, 1)

# 7. updateToolStartStatus: do not open cardEl
old_tool_start = """    // Renderiza card de skeleton dinâmico simulando a estrutura do DecisionCard
    const skeletonHtml = this.renderDecisionCardSkeleton(toolName);
    cardIds.forEach(id => {
      const cardEl = typeof document !== 'undefined' ? document.getElementById(id) : null;
      if (cardEl) {
        cardEl.innerHTML = skeletonHtml;
        cardEl.classList.remove('hidden');
      }
    });"""

new_tool_start = """    // Card estruturado permanece oculto durante a consulta para o texto emergir primeiro
    cardIds.forEach(id => {
      const cardEl = typeof document !== 'undefined' ? document.getElementById(id) : null;
      if (cardEl) {
        cardEl.innerHTML = '';
        cardEl.classList.add('hidden');
      }
    });"""

if old_tool_start not in content:
    print("ERROR: old_tool_start not found")
    sys.exit(1)

content = content.replace(old_tool_start, new_tool_start, 1)

# 8. handleUIComplete signature and options
old_handle_ui_complete = "handleUIComplete(containerId, envelopeData) {"
new_handle_ui_complete = "handleUIComplete(containerId, envelopeData, options = {}) {"

if old_handle_ui_complete not in content:
    print("ERROR: old_handle_ui_complete not found")
    sys.exit(1)

content = content.replace(old_handle_ui_complete, new_handle_ui_complete, 1)

# In handleUIComplete: pass animated to renderCompanionPortalCard
old_portal_call = """      const portalBannerHtml = this.renderCompanionPortalCard({
        artifactId,
        artifactTitle,
        artifactSubtitle,
        containerId,
        widgetHtml: widgetContentHtml,
        startExpanded: startExpanded
      });"""

new_portal_call = """      const portalBannerHtml = this.renderCompanionPortalCard({
        artifactId,
        artifactTitle,
        artifactSubtitle,
        containerId,
        widgetHtml: widgetContentHtml,
        startExpanded: startExpanded,
        animated: !!options.animated
      });"""

if old_portal_call not in content:
    print("ERROR: old_portal_call not found")
    sys.exit(1)

content = content.replace(old_portal_call, new_portal_call, 1)

# In handleUIComplete: fallback card animated class
old_inline_widget = """        if (inlineWidget) {
          hydratedHtml = `
            <div id=\"genui-card-${this.escapeHtml(toolCallId || 'default')}\" 
                 class=\"genui-hydrated-card animate-fade-in my-2\"
                 data-tool-call-id=\"${this.escapeHtml(toolCallId || '')}\"
                 data-component=\"${this.escapeHtml(envelopeData.component_name || '')}\">
              ${inlineWidget}
            </div>
          `;"""

new_inline_widget = """        if (inlineWidget) {
          const entranceClass = options.animated ? 'genui-wow-entrance' : 'animate-fade-in';
          hydratedHtml = `
            <div id=\"genui-card-${this.escapeHtml(toolCallId || 'default')}\" 
                 class=\"genui-hydrated-card ${entranceClass} my-2\"
                 data-tool-call-id=\"${this.escapeHtml(toolCallId || '')}\"
                 data-component=\"${this.escapeHtml(envelopeData.component_name || '')}\">
              ${inlineWidget}
            </div>
          `;"""

if old_inline_widget not in content:
    print("ERROR: old_inline_widget not found")
    sys.exit(1)

content = content.replace(old_inline_widget, new_inline_widget, 1)

# 9. updateToolResultCard: options support
old_update_tool_res = "updateToolResultCard(containerId, toolName, resultData, force = false) {"
new_update_tool_res = "updateToolResultCard(containerId, toolName, resultData, force = false, options = {}) {"

if old_update_tool_res not in content:
    print("ERROR: old_update_tool_res not found")
    sys.exit(1)

content = content.replace(old_update_tool_res, new_update_tool_res, 1)

old_update_tool_portal = """      const portalBannerHtml = this.renderCompanionPortalCard({
        artifactId,
        artifactTitle,
        artifactSubtitle,
        containerId,
        widgetHtml
      });"""

new_update_tool_portal = """      const portalBannerHtml = this.renderCompanionPortalCard({
        artifactId,
        artifactTitle,
        artifactSubtitle,
        containerId,
        widgetHtml,
        animated: !!options.animated
      });"""

if old_update_tool_portal not in content:
    print("ERROR: old_update_tool_portal not found")
    sys.exit(1)

content = content.replace(old_update_tool_portal, new_update_tool_portal, 1)

# 10. renderCompanionPortalCard signature and animated class
old_render_companion = "renderCompanionPortalCard({ artifactId, artifactTitle, artifactSubtitle, containerId, widgetHtml, startExpanded = false }) {"
new_render_companion = "renderCompanionPortalCard({ artifactId, artifactTitle, artifactSubtitle, containerId, widgetHtml, startExpanded = false, animated = false }) {"

if old_render_companion not in content:
    print("ERROR: old_render_companion not found")
    sys.exit(1)

content = content.replace(old_render_companion, new_render_companion, 1)

old_banner_html = """    return `
      <div class="aux-companion-portal-banner aux-artifact-portal-card mb-3 p-3.5 rounded-2xl bg-slate-900/90 border border-cyan-500/30 flex flex-col gap-2.5 shadow-lg backdrop-blur-md">"""

new_banner_html = """    const entranceClass = animated ? 'genui-wow-entrance' : 'animate-fade-in';
    return `
      <div class="aux-companion-portal-banner aux-artifact-portal-card mb-3 p-3.5 rounded-2xl bg-slate-900/90 border border-cyan-500/30 flex flex-col gap-2.5 shadow-lg backdrop-blur-md ${entranceClass}">"""

if old_banner_html not in content:
    print("ERROR: old_banner_html not found")
    sys.exit(1)

content = content.replace(old_banner_html, new_banner_html, 1)

# Save patched file
with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: All 10 UI/UX orchestration patches applied to aura-chat.js")
