"""
Script de aplicacao da Fase 2 do Apendice C: Coreografia Sequencial e Card de Ponte Contextual.
Repositorio: ia-banco-local
Regra estrita: ZERO travessoes Unicode (\u2014 e \u2013) em todo o codigo e comentarios.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
DIST_WEB_DIR = BASE_DIR / "dist" / "AuraBackend" / "_internal" / "web"


def verify_no_unicode_dashes(path: Path) -> None:
    """Verifica que o arquivo nao possui nenhum travessao Unicode."""
    text = path.read_text(encoding="utf-8")
    c_em = text.count("\u2014")
    c_en = text.count("\u2013")
    if c_em > 0 or c_en > 0:
        raise ValueError(
            f"Arquivo {path} contem {c_em} em-dash e {c_en} en-dash proibidos!"
        )
    print(f"[OK] {path.name}: 0 travessoes Unicode encontrados.")


def update_aux_panel() -> None:
    """Ajusta o default de autoOpen para false em web/js/aura-aux-panel.js."""
    aux_path = WEB_DIR / "js" / "aura-aux-panel.js"
    content = aux_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    target = "projectArtifact({ id, containerId, toolName, intent, data, html, autoOpen = true }) {"
    replacement = "projectArtifact({ id, containerId, toolName, intent, data, html, autoOpen = false }) {"

    if target in content_lf:
        content_lf = content_lf.replace(target, replacement, 1)
        print("[AUX] autoOpen default atualizado para false em aura-aux-panel.js.")
    else:
        print("[AUX] autoOpen ja estava configurado com false ou target alterado.")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    aux_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(aux_path)


def update_chat_js() -> None:
    """Ajusta autoOpen: false, applyProgressiveDisclosure e renderCompanionPortalCard em aura-chat.js."""
    chat_path = WEB_DIR / "js" / "aura-chat.js"
    content = chat_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    # 1. autoOpen no hydrateGenUISlot
    target_hydrate = "autoOpen: !isMobile"
    replacement_hydrate = "autoOpen: false"
    if target_hydrate in content_lf:
        content_lf = content_lf.replace(target_hydrate, replacement_hydrate, 1)
        print("[CHAT] 1. autoOpen no hydrateGenUISlot alterado para false.")
    else:
        print("[CHAT] 1. autoOpen no hydrateGenUISlot ja estava atualizado.")

    # 2. autoOpen no renderToolInlineWidget
    target_render = """            intent: resultData?.contrato?.intent || resultData?.intent,
            data: resultData,
            html: widgetHtml,
            autoOpen: true"""
    replacement_render = """            intent: resultData?.contrato?.intent || resultData?.intent,
            data: resultData,
            html: widgetHtml,
            autoOpen: false"""
    if target_render in content_lf:
        content_lf = content_lf.replace(target_render, replacement_render, 1)
        print("[CHAT] 2. autoOpen no renderToolInlineWidget alterado para false.")
    else:
        print("[CHAT] 2. autoOpen no renderToolInlineWidget ja estava atualizado.")

    # 3. applyProgressiveDisclosure: com tool card/canvas, NAO encapsula em disclosure
    old_disclosure_head = """  applyProgressiveDisclosure(htmlContent, isStillStreaming = false, hasToolCard = false) {
    if (!htmlContent || typeof htmlContent !== 'string') return '';
    if (isStillStreaming || !hasToolCard) return htmlContent;"""
    new_disclosure_head = """  applyProgressiveDisclosure(htmlContent, isStillStreaming = false, hasToolCard = false) {
    if (!htmlContent || typeof htmlContent !== 'string') return '';
    if (isStillStreaming) return htmlContent;
    // Apendice C - Fase 2: Com Tool Card/Companion Canvas acoplado, DESATIVA o disclosure no chat.
    // O texto no chat e mantido como resumo fluido executivo, delegando o aprofundamento ao Canvas.
    if (hasToolCard) return htmlContent;"""
    if old_disclosure_head in content_lf:
        content_lf = content_lf.replace(old_disclosure_head, new_disclosure_head, 1)
        print("[CHAT] 3. applyProgressiveDisclosure atualizado para desativar disclosure quando hasToolCard=true.")
    else:
        print("[CHAT] 3. applyProgressiveDisclosure ja estava atualizado.")

    # 4. Redesenho do botao de acao no renderCompanionPortalCard
    old_btn = """            <!-- PC / Desktop: Somente Ver no Painel lateral -->
            <button type="button" onclick="window.auraAuxPanel && window.auraAuxPanel.open('${artifactId}', true, this)" id="${containerId}-btn-open-panel" class="aux-btn-view-panel hidden md:inline-flex px-3 py-1.5 min-h-[36px] rounded-xl bg-gradient-to-r from-cyan-500/20 to-purple-500/20 hover:from-cyan-500/30 hover:to-purple-500/30 text-cyan-200 hover:text-white border border-cyan-500/40 text-xs font-semibold items-center gap-1.5 transition-all active:scale-95 shadow-sm cursor-pointer" title="Abrir no Painel Auxiliar">
              <span>Ver no Painel</span>
              <svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="9 18 15 12 9 6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>"""
    new_btn = """            <!-- PC / Desktop: Convite Contextual para o Canvas lateral (Apendice C - Fase 2) -->
            <button type="button" onclick="window.auraAuxPanel && window.auraAuxPanel.open('${artifactId}', true, this)" id="${containerId}-btn-open-panel" class="aux-btn-view-panel hidden md:inline-flex px-3.5 py-1.5 min-h-[36px] rounded-xl bg-gradient-to-r from-cyan-500/25 via-cyan-500/30 to-blue-600/30 hover:from-cyan-500/40 hover:to-blue-600/40 text-cyan-200 hover:text-white border border-cyan-500/50 text-xs font-semibold items-center gap-1.5 transition-all active:scale-95 shadow-sm cursor-pointer" title="Explorar matriz detalhada e acoes no Canvas lateral">
              <span>Explorar no Canvas -></span>
              <svg class="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="9 18 15 12 9 6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>"""
    if old_btn in content_lf:
        content_lf = content_lf.replace(old_btn, new_btn, 1)
        print("[CHAT] 4. Botao de acao do Companion Portal Card atualizado para 'Explorar no Canvas ->'.")
    else:
        print("[CHAT] 4. Botao de acao do Companion Portal Card ja estava atualizado.")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    chat_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(chat_path)


def update_test_chat_typography() -> None:
    """Atualiza test_chat_typography_ux.py para harmonizar com Apendice C (hasToolCard desativa disclosure)."""
    test_path = BASE_DIR / "tests" / "unit" / "test_chat_typography_ux.py"
    content = test_path.read_text(encoding="utf-8")
    original_crlf = "\r\n" in content
    content_lf = content.replace("\r\n", "\n")

    # 1. Ajuste em test_progressive_disclosure_has_tool_card_rule
    old_test_block = """        # 1. Com tool card ativo (hasToolCard === true) -> Encapsula blocos complementares em disclosure
        assert "aura-chat-disclosure" in data["withToolCard"], (
            "Progressive disclosure deveria estar ativo quando hasToolCard=true e blocos > 3"
        )
        assert "<p>Paragrafo 1</p>" in data["withToolCard"], "Primeiro bloco deve permanecer visivel no topo"
        assert "<p>Paragrafo 2</p>" in data["withToolCard"], "Segundo bloco deve permanecer visivel no topo"

        # 2. Sem tool card (hasToolCard === false) -> Nao deve encapsular
        assert "aura-chat-disclosure" not in data["withoutToolCard"], (
            "Progressive disclosure nao deve ser acionado quando hasToolCard=false"
        )"""

    new_test_block = """        # 1. Com tool card ativo (hasToolCard === true) -> Delegado ao Companion Canvas, SEM disclosure duplicado no chat (Apendice C)
        assert "aura-chat-disclosure" not in data["withToolCard"], (
            "Com tool card ativo, o disclosure deve ser desativado para evitar botoes concorrentes (+Detalhes vs Ver no Painel)"
        )
        assert "<p>Paragrafo 1</p>" in data["withToolCard"]
        assert "<p>Paragrafo 4</p>" in data["withToolCard"]

        # 2. Sem tool card (hasToolCard === false) -> Encapsula blocos complementares em disclosure
        assert "aura-chat-disclosure" in data["withoutToolCard"], (
            "Progressive disclosure deve estar ativo para respostas textuais puras com blocos > 3"
        )
        assert "<p>Paragrafo 1</p>" in data["withoutToolCard"]
        assert "<p>Paragrafo 2</p>" in data["withoutToolCard"]"""

    if old_test_block in content_lf:
        content_lf = content_lf.replace(old_test_block, new_test_block, 1)
        print("[TEST] test_progressive_disclosure_has_tool_card_rule harmonizado com Apendice C.")

    # 2. Ajuste em test_reading_density_toggle_and_modes
    old_toggle_call = """        c.setReadingMode('concise');
        const conciseOutput = c.applyProgressiveDisclosure(html, false, true);

        c.setReadingMode('comfort');
        const comfortMode = c.getReadingMode();
        const comfortOutput = c.applyProgressiveDisclosure(html, false, true);"""

    new_toggle_call = """        c.setReadingMode('concise');
        const conciseOutput = c.applyProgressiveDisclosure(html, false, false);

        c.setReadingMode('comfort');
        const comfortMode = c.getReadingMode();
        const comfortOutput = c.applyProgressiveDisclosure(html, false, false);"""

    if old_toggle_call in content_lf:
        content_lf = content_lf.replace(old_toggle_call, new_toggle_call, 1)
        print("[TEST] test_reading_density_toggle_and_modes atualizado para testar texto puro (hasToolCard=false).")

    final_content = content_lf.replace("\n", "\r\n") if original_crlf else content_lf
    test_path.write_text(final_content, encoding="utf-8")
    verify_no_unicode_dashes(test_path)


def sync_dist() -> None:
    """Sincroniza arquivos de web/ para dist/AuraBackend/_internal/web/."""
    for rel_path in ["js/aura-chat.js", "js/aura-aux-panel.js"]:
        src = WEB_DIR / rel_path
        dst = DIST_WEB_DIR / rel_path
        if src.exists() and dst.parent.exists():
            shutil.copy2(src, dst)
            print(f"[SYNC] Sincronizado: {rel_path} -> dist/")


if __name__ == "__main__":
    print("Iniciando aplicacao da Fase 2...")
    update_aux_panel()
    update_chat_js()
    update_test_chat_typography()
    sync_dist()
    print("Fase 2 aplicada com sucesso!")
