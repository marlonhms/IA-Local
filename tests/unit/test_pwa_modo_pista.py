"""
Testes Unitarios do PWA Mobile Modo Pista com Comandos de Voz (Fase P3-4).
Valida o manifesto PWA (web/manifest.json), o service worker offline (web/sw.js),
o controlador de comandos por voz Web Speech API (web/js/aura-voice.js),
as rotas FastAPI correspondentes e a regra inegociavel de ZERO travessoes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config.settings import BASE_DIR
from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory


@pytest.mark.unit
class TestPWAModoPista:
    """Suite de testes para garantia de integridade do PWA Mobile e Modo Pista."""

    @classmethod
    def setup_class(cls) -> None:
        """Inicializa caminhos e cliente de teste FastAPI."""
        cls.web_dir = BASE_DIR / "web"
        cls.manifest_path = cls.web_dir / "manifest.json"
        cls.sw_path = cls.web_dir / "sw.js"
        cls.voice_path = cls.web_dir / "js" / "aura-voice.js"
        cls.css_path = cls.web_dir / "css" / "aura.css"
        cls.index_path = cls.web_dir / "index.html"

        mem = AuraSessionMemory(db_path=":memory:")
        engine = AuraEngine(tenant_id="test_pwa", filial_id="posto_pwa", session_memory=mem)
        cls.app = create_aura_app(engine)
        cls.client = TestClient(cls.app)

    def test_manifest_json_integrity(self) -> None:
        """Valida que web/manifest.json existe e contem todos os campos obrigatorios do PWA."""
        assert self.manifest_path.exists(), f"Manifesto PWA nao encontrado: {self.manifest_path}"
        content = self.manifest_path.read_text(encoding="utf-8")
        data = json.loads(content)

        assert data.get("name") == "AURA | Inteligência e Operação de Pista"
        assert data.get("short_name") == "AURA Pista"
        assert data.get("start_url") == "/"
        assert data.get("display") == "standalone"
        assert data.get("background_color") == "#07090e"
        assert data.get("theme_color") == "#06b6d4"
        assert data.get("orientation") in ["any", "portrait", "landscape"]

        # Validacao de icones declarados
        icons = data.get("icons", [])
        assert len(icons) >= 1, "Manifesto PWA deve conter pelo menos 1 icone"
        for icon in icons:
            src = icon.get("src", "")
            assert not src.startswith("http://") and not src.startswith("https://") and not src.startswith("//"), (
                f"Icone no manifesto nao pode apontar para CDN externa: {src}"
            )
            assert "sizes" in icon and "type" in icon

    def test_service_worker_offline_first_and_cache_strategies(self) -> None:
        """Valida eventos de ciclo de vida e estrategias de cache offline do sw.js."""
        assert self.sw_path.exists(), f"Service Worker nao encontrado: {self.sw_path}"
        sw_content = self.sw_path.read_text(encoding="utf-8")

        # Verifica eventos essenciais de service worker
        assert "addEventListener('install'" in sw_content or 'addEventListener("install"' in sw_content
        assert "addEventListener('activate'" in sw_content or 'addEventListener("activate"' in sw_content
        assert "addEventListener('fetch'" in sw_content or 'addEventListener("fetch"' in sw_content

        # Verifica presenca de cache local e manipulacao de navegacao e assets
        assert "caches.open" in sw_content
        assert "CACHE_NAME" in sw_content
        assert "PRECACHE_ASSETS" in sw_content
        assert "aura-voice.js" in sw_content

        # Proibicao estrita de CDNs externas no Service Worker
        for cdn in ["unpkg.com", "cdn.tailwindcss", "jsdelivr.net", "cdnjs", "googleapis.com"]:
            assert cdn not in sw_content, f"Service Worker referencia CDN externa proibida: {cdn}"

    def test_fastapi_serves_manifest_and_service_worker(self) -> None:
        """Valida que a API FastAPI serve /manifest.json e /sw.js com content-types padronizados."""
        # 1. Rota /manifest.json
        resp_manifest = self.client.get("/manifest.json")
        assert resp_manifest.status_code == 200
        assert "application/manifest+json" in resp_manifest.headers.get("content-type", "")
        manifest_data = resp_manifest.json()
        assert manifest_data.get("short_name") == "AURA Pista"

        # 2. Rota /sw.js
        resp_sw = self.client.get("/sw.js")
        assert resp_sw.status_code == 200
        assert "javascript" in resp_sw.headers.get("content-type", "")
        assert resp_sw.headers.get("service-worker-allowed") == "/"
        assert "CACHE_NAME" in resp_sw.text

    def test_index_html_contains_pwa_tags_and_voice_elements(self) -> None:
        """Valida tags de PWA, botoes de Modo Pista e Voz no index.html."""
        assert self.index_path.exists(), f"index.html nao encontrado: {self.index_path}"
        html = self.index_path.read_text(encoding="utf-8")

        # Links e meta tags PWA
        assert '<link rel="manifest" href="/manifest.json">' in html
        assert 'name="theme-color" content="#06b6d4"' in html
        assert 'name="mobile-web-app-capable" content="yes"' in html
        assert 'name="apple-mobile-web-app-capable" content="yes"' in html
        assert 'name="apple-mobile-web-app-title" content="AURA Pista"' in html

        # Botoes de Modo Pista (Header e Sidebar)
        assert 'id="btn-toggle-modo-pista"' in html
        assert 'id="sidebar-btn-toggle-modo-pista"' in html
        assert 'id="modo-pista-badge"' in html

        # Botao e Indicador de Voz (Web Speech API)
        assert 'id="btn-voice-input"' in html
        assert 'id="voice-recording-indicator"' in html
        assert 'Ouvindo comando de pista...' in html

        # Scripts necessarios
        assert "aura-voice.js" in html
        assert "navigator.serviceWorker.register('/sw.js'" in html or 'navigator.serviceWorker.register("/sw.js"' in html

    def test_css_modo_pista_and_voice_animation(self) -> None:
        """Valida classes CSS do Modo Pista de alto contraste e animacao de gravacao de voz."""
        assert self.css_path.exists(), f"aura.css nao encontrado: {self.css_path}"
        css = self.css_path.read_text(encoding="utf-8")

        # Classe .modo-pista
        assert ".modo-pista" in css
        assert "#000000" in css
        assert "min-height: 48px" in css

        # Animacao de voz
        assert "voice-recording-pulsing" in css
        assert "pulse-voice" in css

    def test_aura_voice_js_integrity(self) -> None:
        """Valida arquivo aura-voice.js com suporte a Web Speech API pt-BR e tolerancia defensiva."""
        assert self.voice_path.exists(), f"aura-voice.js nao encontrado: {self.voice_path}"
        voice_code = self.voice_path.read_text(encoding="utf-8")

        assert "SpeechRecognition" in voice_code
        assert "webkitSpeechRecognition" in voice_code
        assert "pt-BR" in voice_code
        assert "btn-voice-input" in voice_code
        assert "chat-input-text" in voice_code
        assert "toggleVoice" in voice_code

    def test_all_precache_assets_served_with_200(self) -> None:
        """Valida que absolutamente todos os assets listados em PRECACHE_ASSETS no sw.js retornam HTTP 200."""
        sw_content = self.sw_path.read_text(encoding="utf-8")
        import re
        match = re.search(r'const\s+PRECACHE_ASSETS\s*=\s*\[([\s\S]*?)\];', sw_content)
        assert match is not None, "Constante PRECACHE_ASSETS nao encontrada em sw.js"
        assets_raw = match.group(1)
        assets = [
            asset.strip().strip("'\"")
            for asset in assets_raw.split(",")
            if asset.strip() and not asset.strip().startswith("//")
        ]
        assert len(assets) >= 15, f"Quantidade insuficiente de assets no precache: {len(assets)}"

        for asset in assets:
            resp = self.client.get(asset)
            assert resp.status_code == 200, (
                f"Asset de precache retornou HTTP {resp.status_code} ao inves de 200: {asset}"
            )
            assert len(resp.content) > 0, f"Asset de precache vazio: {asset}"

    def test_manifest_icons_served_with_200(self) -> None:
        """Valida que todos os icones declarados no manifest.json sao servidos com HTTP 200 pela API."""
        content = self.manifest_path.read_text(encoding="utf-8")
        data = json.loads(content)
        icons = data.get("icons", [])
        assert len(icons) >= 2, "Manifesto deve conter pelo menos 2 icones declarados"

        for icon in icons:
            src = icon["src"]
            resp = self.client.get(src)
            assert resp.status_code == 200, f"Icone do manifesto falhou com status {resp.status_code}: {src}"
            assert "svg" in resp.headers.get("content-type", "") or "icon" in resp.headers.get("content-type", "")

    def test_sw_uses_ignore_search_for_versioned_assets(self) -> None:
        """Valida que o service worker utiliza ignoreSearch: true para suportar querystrings de versao."""
        sw_content = self.sw_path.read_text(encoding="utf-8")
        assert "ignoreSearch: true" in sw_content, "Service worker deve especificar ignoreSearch: true para match offline"

    def test_aura_voice_transcript_concatenation_and_autosend(self) -> None:
        """Valida concatenacao sem perda de interim e suporte a autoSend no controlador de voz."""
        voice_code = self.voice_path.read_text(encoding="utf-8")
        assert "finalTranscript + interimTranscript" in voice_code, (
            "Controlador de voz deve somar finalTranscript e interimTranscript para nao engolir falas parciais"
        )
        assert "setAutoSend" in voice_code
        assert "this.autoSend" in voice_code
        assert "dispatchEvent" in voice_code

    def test_modo_pista_touch_targets_48px_in_html(self) -> None:
        """Valida que botoes criticos de pista possuem alvo tátil mínimo de 48px diretamente no HTML."""
        html = self.index_path.read_text(encoding="utf-8")
        assert 'id="btn-toggle-modo-pista"' in html
        assert 'min-h-[48px]' in html
        assert 'id="btn-voice-input"' in html
        assert 'min-h-[48px] min-w-[48px]' in html
        assert 'id="btn-chat-send"' in html

    def test_fastapi_serves_icon_and_index_routes(self) -> None:
        """Valida que a API serve rotas auxiliares /icon.svg e /index.html."""
        resp_icon = self.client.get("/icon.svg")
        assert resp_icon.status_code == 200
        assert "image/svg+xml" in resp_icon.headers.get("content-type", "")

        resp_static_icon = self.client.get("/static/icon.svg")
        assert resp_static_icon.status_code == 200

        resp_index = self.client.get("/index.html")
        assert resp_index.status_code == 200
        assert "text/html" in resp_index.headers.get("content-type", "")

    def test_aura_app_modo_pista_theme_color_and_shortcut(self) -> None:
        """Valida atualizacao dinamica de theme-color e atalho Alt+P em aura-app.js."""
        app_js = (self.web_dir / "js" / "aura-app.js").read_text(encoding="utf-8")
        assert "metaThemeColor" in app_js
        assert "theme-color" in app_js
        assert "altKey" in app_js
        assert "aura_modo_pista" in app_js

    def test_zero_travessoes_in_pwa_files(self) -> None:
        """Garante a regra inegociavel de ZERO travessoes (\u2014 e \u2013) em todos os arquivos da Fase P3-4."""
        files_to_check = [
            Path(__file__),
            self.manifest_path,
            self.sw_path,
            self.voice_path,
            self.index_path,
            self.css_path,
            self.web_dir / "js" / "aura-app.js",
            BASE_DIR / "core" / "aura_api.py",
        ]

        for file_path in files_to_check:
            content = file_path.read_text(encoding="utf-8")
            assert "\u2014" not in content, f"Travessao em-dash (\u2014) encontrado no arquivo: {file_path}"
            assert "\u2013" not in content, f"Travessao en-dash (\u2013) encontrado no arquivo: {file_path}"
