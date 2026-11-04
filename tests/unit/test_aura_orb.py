"""
Testes Unitarios do AuraLivingOrb Web e Modal Imersivo de Voz
Valida experiencia de voz estilo Gemini/GPT, remocao do 'A' redondo da frente e zero travessoes.
"""

import os
import hashlib
from pathlib import Path
import pytest

WEB_DIR = Path(__file__).resolve().parent.parent.parent / "web"
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "dist" / "AuraBackend" / "_internal" / "web"


def file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def test_ic_aura_logo_assets_exist():
    """Garante que os ativos visuais oficiais estao presentes no web e no dist."""
    web_img = WEB_DIR / "img" / "ic_aura_logo.png"
    web_static_img = WEB_DIR / "static" / "img" / "ic_aura_logo.png"
    dist_img = DIST_DIR / "img" / "ic_aura_logo.png"
    dist_static_img = DIST_DIR / "static" / "img" / "ic_aura_logo.png"

    assert web_img.exists(), "web/img/ic_aura_logo.png nao encontrado"
    assert web_static_img.exists(), "web/static/img/ic_aura_logo.png nao encontrado"
    assert dist_img.exists(), "dist/.../web/img/ic_aura_logo.png nao encontrado"
    assert dist_static_img.exists(), "dist/.../web/static/img/ic_aura_logo.png nao encontrado"

    assert web_img.stat().st_size > 100_000
    assert file_sha256(web_img) == file_sha256(dist_img)
    assert file_sha256(web_static_img) == file_sha256(dist_static_img)


def test_pure_living_orb_no_round_letter_a():
    """Garante que o orbe e puro, sem o 'A' redondo na frente, e sem bolinha branca pulsando."""
    orb_js = WEB_DIR / "js" / "aura-orb.js"
    with open(orb_js, "r", encoding="utf-8") as f:
        js_content = f.read()

    # Nao deve desenhar o emblema estatico com letra A sobreposto ao orbe vivo
    assert "drawAuraAvatarEmblem" not in js_content
    assert "showLetter" not in js_content

    # No index.html, os orbes do header e drawer nao contem <span>A</span>
    html_file = WEB_DIR / "index.html"
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    assert '<div id="header-neural-core-orb" class="neural-core-orb"></div>' in html_content
    assert '<div id="drawer-neural-core-orb" class="neural-core-orb !w-8 !h-8"></div>' in html_content

    # No CSS, a bolinha branca pulsante ::after continua desativada
    css_file = WEB_DIR / "css" / "aura.css"
    with open(css_file, "r", encoding="utf-8") as f:
        css_content = f.read()

    assert ".neural-core-orb::after" in css_content
    assert "display: none !important" in css_content


def test_aura_living_orb_js_engine_parity():
    """Garante que aura-orb.js implementa o motor de ondas senoidais polares do AuraLivingOrb."""
    orb_js = WEB_DIR / "js" / "aura-orb.js"
    with open(orb_js, "r", encoding="utf-8") as f:
        content = f.read()

    expected_emotions = [
        "NEUTRAL",
        "CALM",
        "THINKING",
        "LISTENING",
        "WORRIED",
        "AGITATED",
        "SUCCESS",
    ]

    for em in expected_emotions:
        assert f"{em}: '{em}'" in content, f"Emocao {em} ausente no AuraOrbEmotion JS"

    # Valida funcoes e classes do AuraLivingOrb puro e AuraVoiceManager
    assert "buildLiquidPath" in content
    assert "sampleVoiceRms" in content
    assert "class AuraOrbAudioTracker" in content
    assert "class AuraOrb" in content
    assert "class AuraOrbManager" in content
    assert "window.auraOrbManager" in content or "root.auraOrbManager" in content


def test_aura_voice_modal_immersion():
    """Garante remocao do botao flutuante inferior e presenca do modal imersivo de voz."""
    html_file = WEB_DIR / "index.html"
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    # Botao flutuante inferior foi removido
    assert "aura-floating-orb-container" not in html

    # Modal imersivo de voz esta presente com todos os seus elementos
    assert 'id="aura-voice-modal-overlay"' in html
    assert 'id="aura-voice-scrim"' in html
    assert 'id="aura-voice-modal-card"' in html
    assert 'id="aura-voice-modal-orb-container"' in html
    assert 'id="aura-voice-transcription-preview"' in html
    assert 'id="btn-voice-modal-close"' in html
    assert 'id="btn-voice-modal-send"' in html
    assert 'id="btn-voice-modal-clear"' in html


def test_aura_css_voice_modal_styles():
    """Garante estilizacao correta do modal de voz e ausencia de deformacao de escala."""
    css_file = WEB_DIR / "css" / "aura.css"
    with open(css_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "#aura-voice-modal-overlay" in content
    assert "#aura-voice-modal-card" in content
    assert "#aura-voice-modal-orb-container" in content
    assert ".aura-floating-orb-container" not in content


def test_zero_unicode_dashes_in_orb_artifacts():
    """Regra inegociavel: ZERO travessoes unicode em todos os arquivos modificados."""
    target_files = [
        WEB_DIR / "js" / "aura-orb.js",
        WEB_DIR / "js" / "aura-voice.js",
        WEB_DIR / "js" / "aura-chat.js",
        WEB_DIR / "css" / "aura.css",
        WEB_DIR / "index.html",
        DIST_DIR / "js" / "aura-orb.js",
        DIST_DIR / "js" / "aura-voice.js",
        DIST_DIR / "js" / "aura-chat.js",
        DIST_DIR / "css" / "aura.css",
        DIST_DIR / "index.html",
        WEB_DIR / "js" / "aura-genui-widgets.js",
        DIST_DIR / "js" / "aura-genui-widgets.js",
    ]

    for p in target_files:
        assert p.exists(), f"Arquivo nao encontrado: {p}"
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        assert "\u2014" not in text, f"Em-dash encontrado no arquivo {p.name}"
        assert "\u2013" not in text, f"En-dash encontrado no arquivo {p.name}"


def test_web_and_dist_sync():
    """Garante sincronizacao byte-a-byte entre web e dist para os arquivos modificados."""
    synced_rel_paths = [
        "img/ic_aura_logo.png",
        "static/img/ic_aura_logo.png",
        "js/aura-orb.js",
        "js/aura-voice.js",
        "js/aura-chat.js",
        "css/aura.css",
        "index.html",
        "js/aura-genui-widgets.js",
    ]

    for rel in synced_rel_paths:
        src = WEB_DIR / rel
        dst = DIST_DIR / rel
        assert src.exists(), f"Arquivo fonte ausente: {src}"
        assert dst.exists(), f"Arquivo destino ausente: {dst}"
        assert file_sha256(src) == file_sha256(dst), f"Dessincronizacao de hash em {rel}"
