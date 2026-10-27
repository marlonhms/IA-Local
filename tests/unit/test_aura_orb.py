"""
Testes Unitarios do AuraOrb Web e Paridade com Aura Assistance Android
Valida AuraLivingOrb, AuraAvatar, AuraBrandTitle, reatividade de audio e zero travessoes.
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


def test_aura_assistance_android_avatar_and_logo_parity():
    """Garante paridade exata com AuraAvatar e AuraBrandTitle do Aura Assistance Android."""
    css_file = WEB_DIR / "css" / "aura.css"
    with open(css_file, "r", encoding="utf-8") as f:
        content = f.read()

    # AuroraBrush no background do Avatar: linear-gradient(135deg, #22d3ee 0%, #10b981 100%)
    assert "#22d3ee" in content and "#10b981" in content
    # Tipografia Newsreader oficial
    assert "'Newsreader'" in content
    # Letra A em ObsidianBase (#07090E)
    assert "#07090e" in content
    # AuraBrandTitle com AuraBrandGradient (#38bdf8, #0d9488, #a855f7)
    assert ".aura-brand-title" in content
    assert "#38bdf8" in content and "#0d9488" in content and "#a855f7" in content

    # Suprime a bolinha interna legada que ficava crescendo e diminuindo
    assert ".neural-core-orb::after" in content
    assert "display: none !important" in content


def test_aura_living_orb_js_engine_parity():
    """Garante que aura-orb.js implementa o motor de ondas senoidais polares do AuraLivingOrb."""
    orb_js = WEB_DIR / "js" / "aura-orb.js"
    assert orb_js.exists(), "web/js/aura-orb.js nao encontrado"

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

    # Valida funcoes e classes do AuraLivingOrb e AuraVoiceManager
    assert "buildLiquidPath" in content
    assert "drawAuraAvatarEmblem" in content
    assert "sampleVoiceRms" in content
    assert "class AuraOrbAudioTracker" in content
    assert "class AuraOrb" in content
    assert "class AuraFloatingOrb" in content
    assert "class AuraOrbManager" in content
    assert "window.auraOrbManager" in content or "root.auraOrbManager" in content


def test_aura_css_no_growing_shrinking_balls():
    """Garante que as animacoes de escala pulsatil foram removidas do CSS."""
    css_file = WEB_DIR / "css" / "aura.css"
    with open(css_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Verifica presenca das novas classes
    assert ".aura-orb-host" in content
    assert ".aura-orb-canvas" in content
    assert ".aura-floating-orb-container" in content
    assert ".aura-floating-orb-badge" in content

    # Verifica que as animacoes de pulso continuo nao deformam a escala
    assert "@keyframes pulse-voice" in content
    voice_block = content.split("@keyframes pulse-voice")[1].split("}")[0]
    assert "transform: scale" not in voice_block

    assert "@keyframes pulseCore" in content
    core_block = content.split("@keyframes pulseCore")[1].split("}")[0]
    assert "transform: scale" not in core_block

    assert "@keyframes cognitiveOrbPulse" in content
    cog_block = content.split("@keyframes cognitiveOrbPulse")[1].split("}")[0]
    assert "transform: scale" not in cog_block


def test_index_html_integration():
    """Garante inclusao de aura-orb.js e presenca dos containers e brand title no index.html."""
    html_file = WEB_DIR / "index.html"
    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert '<script src="/static/js/aura-orb.js?v=2.10.22"></script>' in content
    assert 'id="header-neural-core-orb"' in content
    assert 'id="drawer-neural-core-orb"' in content
    assert 'id="aura-floating-orb-container"' in content
    assert 'class="aura-brand-title' in content


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
    ]

    for rel in synced_rel_paths:
        src = WEB_DIR / rel
        dst = DIST_DIR / rel
        assert src.exists(), f"Arquivo fonte ausente: {src}"
        assert dst.exists(), f"Arquivo destino ausente: {dst}"
        assert file_sha256(src) == file_sha256(dst), f"Dessincronizacao de hash em {rel}"
